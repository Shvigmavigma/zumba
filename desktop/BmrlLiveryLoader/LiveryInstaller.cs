using System.IO.Compression;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace BmrlLiveryLoader;

public sealed record InstallSummary(string SkinFolder, int InstalledFiles, IReadOnlyList<string> SkippedFiles);
public sealed record BulkInstallSummary(
    int TotalLiveries,
    int SuccessfulLiveries,
    int InstalledFiles,
    IReadOnlyList<string> SkippedFiles,
    IReadOnlyList<string> FailedLiveries);
public sealed record LoaderUpdate(Version Version, Uri DownloadUri);

public static class LiveryInstaller
{
    private const string WebsiteRoot = "https://bmrl.site/";
    private const string VersionManifestUrl = "https://bmrl.site/downloads/livery-loader-version.json";
    private const long MaxArchiveBytes = 500L * 1024 * 1024;
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromMinutes(5) };
    private static readonly Regex ProfileIdPattern = new(
        @"^(?:(?:https?://[^/]+)?/pilots/)?(?<id>\d+)(?:[/?#].*)?$",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant | RegexOptions.Compiled);

    public static async Task<LoaderUpdate?> CheckForUpdateAsync(CancellationToken cancellationToken = default)
    {
        var installedVersion = typeof(LiveryInstaller).Assembly.GetName().Version ?? new Version(0, 0, 0);
        using var request = new HttpRequestMessage(HttpMethod.Get, VersionManifestUrl);
        request.Headers.CacheControl = new CacheControlHeaderValue { NoCache = true, NoStore = true };
        using var response = await Http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
        response.EnsureSuccessStatusCode();
        if (response.Content.Headers.ContentLength is > 16 * 1024)
            throw new InvalidDataException("The loader version manifest is too large.");

        var manifest = await response.Content.ReadFromJsonAsync<LoaderVersionManifest>(cancellationToken: cancellationToken);
        if (manifest is null || !IsNewerVersion(installedVersion, manifest.Version)) return null;
        if (!Uri.TryCreate(new Uri(WebsiteRoot), manifest.DownloadPath, out var downloadUri)
            || downloadUri.Scheme != Uri.UriSchemeHttps
            || !string.Equals(downloadUri.Host, new Uri(WebsiteRoot).Host, StringComparison.OrdinalIgnoreCase)
            || !downloadUri.AbsolutePath.StartsWith("/downloads/", StringComparison.Ordinal))
            throw new InvalidDataException("The loader update URL is not a trusted BMRL download.");

        return new LoaderUpdate(Version.Parse(manifest.Version!), downloadUri);
    }

    public static bool IsNewerVersion(Version installedVersion, string? latestVersion) =>
        Version.TryParse(latestVersion, out var latest) && latest > installedVersion;

    public static async Task<InstallSummary> InstallAsync(
        string profileInput,
        string carsFolder,
        string liveriesFolder,
        IProgress<string>? progress = null,
        CancellationToken cancellationToken = default)
    {
        if (!TryParseProfileId(profileInput, out var userId))
            throw new InvalidOperationException("Введите числовой ID пилота или ссылку на его публичный профиль.");
        if (!Directory.Exists(carsFolder)) throw new DirectoryNotFoundException("Не найдена папка Cars. Выберите папку ACC вручную.");
        if (!Directory.Exists(liveriesFolder)) throw new DirectoryNotFoundException("Не найдена папка Liveries. Выберите папку ACC вручную.");

        progress?.Report("Получаю данные ливреи…");
        using var metadataResponse = await Http.GetAsync(
            new Uri(new Uri(WebsiteRoot), $"api/users/{userId}/livery"),
            HttpCompletionOption.ResponseHeadersRead,
            cancellationToken);
        if (metadataResponse.StatusCode == HttpStatusCode.NotFound)
            throw new InvalidOperationException("Профиль не найден или в нём нет доступной ливреи.");
        metadataResponse.EnsureSuccessStatusCode();

        var metadata = await metadataResponse.Content.ReadFromJsonAsync<LiveryMetadata>(cancellationToken: cancellationToken);
        if (metadata is null) throw new InvalidOperationException("В этом профиле пока нет загруженной ливреи.");
        ValidateMetadata(metadata, userId);

        var cacheRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "BMRL", "LiveryLoader");
        var packageCache = Path.Combine(cacheRoot, $"{userId}-{metadata.PackageId}");
        Directory.CreateDirectory(packageCache);
        var carsZip = Path.Combine(packageCache, "cars.zip");
        var liveriesZip = Path.Combine(packageCache, "liveries.zip");

        await DownloadArchiveIfMissingAsync(metadata.CarsArchiveUrl!, carsZip, progress, "Скачиваю JSON автомобиля…", cancellationToken);
        await DownloadArchiveIfMissingAsync(metadata.LiveriesArchiveUrl!, liveriesZip, progress, "Скачиваю папку ливреи…", cancellationToken);
        progress?.Report("Проверяю содержимое архивов…");
        var result = InstallArchives(carsZip, liveriesZip, carsFolder, liveriesFolder);
        PruneOldCache(cacheRoot, userId, metadata.PackageId!);
        return result;
    }

    public static async Task<BulkInstallSummary> InstallAllAsync(
        string carsFolder,
        string liveriesFolder,
        IProgress<string>? progress = null,
        CancellationToken cancellationToken = default)
    {
        if (!Directory.Exists(carsFolder)) throw new DirectoryNotFoundException("Не найдена папка Cars. Выберите папку ACC вручную.");
        if (!Directory.Exists(liveriesFolder)) throw new DirectoryNotFoundException("Не найдена папка Liveries. Выберите папку ACC вручную.");

        progress?.Report("Получаю список ливрей BMRL…");
        using var response = await Http.GetAsync(
            new Uri(new Uri(WebsiteRoot), "api/users/liveries"),
            HttpCompletionOption.ResponseHeadersRead,
            cancellationToken);
        response.EnsureSuccessStatusCode();
        var catalog = await response.Content.ReadFromJsonAsync<List<LiveryMetadata>>(cancellationToken: cancellationToken)
            ?? throw new InvalidDataException("Сервер вернул некорректный список ливрей.");
        if (catalog.Count == 0) return new BulkInstallSummary(0, 0, 0, [], []);

        var cacheRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "BMRL", "LiveryLoader");
        Directory.CreateDirectory(cacheRoot);
        var skipped = new List<string>();
        var failures = new List<string>();
        var successful = 0;
        var installedFiles = 0;

        for (var index = 0; index < catalog.Count; index++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var metadata = catalog[index];
            var pilot = string.IsNullOrWhiteSpace(metadata.PilotName)
                ? $"Пилот #{metadata.PilotNumber}"
                : $"#{metadata.PilotNumber} · {metadata.PilotName}";
            progress?.Report($"Устанавливаю ливрею {index + 1} из {catalog.Count}: {pilot}…");

            try
            {
                ValidateMetadata(metadata);
                var packageCache = Path.Combine(cacheRoot, $"{metadata.UserId}-{metadata.PackageId}");
                Directory.CreateDirectory(packageCache);
                var carsZip = Path.Combine(packageCache, "cars.zip");
                var liveriesZip = Path.Combine(packageCache, "liveries.zip");

                await DownloadArchiveIfMissingAsync(
                    metadata.CarsArchiveUrl!, carsZip, progress, $"Скачиваю JSON для {pilot}…", cancellationToken);
                await DownloadArchiveIfMissingAsync(
                    metadata.LiveriesArchiveUrl!, liveriesZip, progress, $"Скачиваю ливрею для {pilot}…", cancellationToken);
                cancellationToken.ThrowIfCancellationRequested();
                var result = InstallArchives(carsZip, liveriesZip, carsFolder, liveriesFolder);
                installedFiles += result.InstalledFiles;
                skipped.AddRange(result.SkippedFiles.Select(path => $"{pilot}: {path}"));
                successful++;
                PruneOldCache(cacheRoot, metadata.UserId, metadata.PackageId!);
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
            {
                throw;
            }
            catch (Exception ex)
            {
                failures.Add($"{pilot}: {ex.Message}");
            }
        }

        return new BulkInstallSummary(catalog.Count, successful, installedFiles, skipped, failures);
    }

    public static InstallSummary InstallArchives(string carsArchivePath, string liveriesArchivePath, string carsFolder, string liveriesFolder)
    {
        if (!Directory.Exists(carsFolder)) throw new DirectoryNotFoundException("Папка Cars не существует.");
        if (!Directory.Exists(liveriesFolder)) throw new DirectoryNotFoundException("Папка Liveries не существует.");

        using var cars = ZipFile.OpenRead(carsArchivePath);
        using var liveries = ZipFile.OpenRead(liveriesArchivePath);
        var carEntries = cars.Entries.Where(entry => !IsDirectory(entry)).ToArray();
        if (carEntries.Length != 1 || carEntries[0].FullName.Contains('/') || !carEntries[0].FullName.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Архив Cars должен содержать один JSON-файл в корне архива.");

        var skinFolder = ReadSkinFolder(carEntries[0]);
        var liveryEntries = liveries.Entries.Where(entry => !IsDirectory(entry)).ToArray();
        if (liveryEntries.Length == 0) throw new InvalidDataException("Архив Liveries пуст.");
        foreach (var entry in liveries.Entries)
        {
            if (IsDirectory(entry))
            {
                var directoryName = entry.FullName.TrimEnd('/');
                if (!string.IsNullOrEmpty(directoryName)) ValidateLiveryMember(directoryName, skinFolder);
            }
            else
            {
                ValidateLiveryMember(entry.FullName, skinFolder);
            }
        }

        var skipped = new List<string>();
        var installed = ExtractArchive(cars, carsFolder, skipped);
        installed += ExtractArchive(liveries, liveriesFolder, skipped);
        return new InstallSummary(skinFolder, installed, skipped);
    }

    public static void RunSelfTest()
    {
        if (!IsNewerVersion(new Version(1, 0, 0, 0), "1.0.1")
            || IsNewerVersion(new Version(1, 0, 0, 0), "1.0.0.0")
            || IsNewerVersion(new Version(1, 0, 0, 0), "latest"))
            throw new InvalidOperationException("Loader update version comparison self-test failed.");
        if (!TryParseProfileId("https://bmrl.site/pilots/58", out var parsedUserId) || parsedUserId != 58)
            throw new InvalidOperationException("Loader pilot profile URL self-test failed.");
        if (ResolveAssetUri("/api/users/58/livery-assets/package/cars.zip").Host != new Uri(WebsiteRoot).Host)
            throw new InvalidOperationException("Loader trusted archive URL self-test failed.");
        try
        {
            ResolveAssetUri("https://example.com/archive.zip");
            throw new InvalidOperationException("Loader accepted an untrusted archive URL.");
        }
        catch (InvalidDataException)
        {
        }

        var testRoot = Path.Combine(Path.GetTempPath(), $"bmrl-livery-check-{Guid.NewGuid():N}");
        var carsFolder = Path.Combine(testRoot, "Cars");
        var liveriesFolder = Path.Combine(testRoot, "Liveries");
        var carsZip = Path.Combine(testRoot, "cars.zip");
        var liveriesZip = Path.Combine(testRoot, "liveries.zip");
        Directory.CreateDirectory(carsFolder);
        Directory.CreateDirectory(liveriesFolder);
        try
        {
            using (var archive = ZipFile.Open(carsZip, ZipArchiveMode.Create))
            using (var stream = archive.CreateEntry("0-car.json").Open())
            {
                var json = Encoding.Unicode.GetBytes("{\"customSkinName\":\"sui\"}");
                stream.Write(json);
            }
            using (var archive = ZipFile.Open(liveriesZip, ZipArchiveMode.Create))
            using (var stream = archive.CreateEntry("sui/livery.json").Open())
            {
                var bytes = Encoding.UTF8.GetBytes("{} ");
                stream.Write(bytes);
            }

            var carPath = Path.Combine(carsFolder, "0-car.json");
            File.WriteAllText(carPath, "keep existing file");
            var cachedArchive = Path.Combine(testRoot, "cached.zip");
            var duplicateDownload = Path.Combine(testRoot, "cached.zip.part");
            File.WriteAllText(cachedArchive, "completed download");
            File.WriteAllText(duplicateDownload, "duplicate download");
            MoveDownloadedArchiveIntoCache(duplicateDownload, cachedArchive);
            if (File.ReadAllText(cachedArchive) != "completed download" || File.Exists(duplicateDownload))
                throw new InvalidOperationException("Livery loader self-test failed on a concurrent archive cache download.");

            var result = InstallArchives(carsZip, liveriesZip, carsFolder, liveriesFolder);
            if (result.SkinFolder != "sui" || result.InstalledFiles != 1 || result.SkippedFiles.Count != 1)
                throw new InvalidOperationException("Livery loader self-test failed on exact folder or conflict handling.");
            if (File.ReadAllText(carPath) != "keep existing file")
                throw new InvalidOperationException("Livery loader self-test overwrote an existing Cars file.");
            if (!File.Exists(Path.Combine(liveriesFolder, "sui", "livery.json")))
                throw new InvalidOperationException("Livery loader self-test did not preserve the exact ACC folder name.");
        }
        finally
        {
            Directory.Delete(testRoot, recursive: true);
        }
    }

    private static async Task DownloadArchiveIfMissingAsync(
        string path,
        string targetPath,
        IProgress<string>? progress,
        string progressMessage,
        CancellationToken cancellationToken)
    {
        if (File.Exists(targetPath) && new FileInfo(targetPath).Length > 0) return;
        progress?.Report(progressMessage);
        var requestUri = ResolveAssetUri(path);
        var temporaryPath = $"{targetPath}.{Guid.NewGuid():N}.part";
        try
        {
            using var response = await Http.GetAsync(requestUri, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
            response.EnsureSuccessStatusCode();
            if (response.Content.Headers.ContentLength is > MaxArchiveBytes)
                throw new InvalidDataException("Архив больше допустимых 500 МБ.");
            await using var source = await response.Content.ReadAsStreamAsync(cancellationToken);
            await using var target = new FileStream(temporaryPath, FileMode.CreateNew, FileAccess.Write, FileShare.None, 1024 * 1024, useAsync: true);
            var buffer = new byte[1024 * 1024];
            long total = 0;
            while (true)
            {
                var read = await source.ReadAsync(buffer, cancellationToken);
                if (read == 0) break;
                total += read;
                if (total > MaxArchiveBytes) throw new InvalidDataException("Архив больше допустимых 500 МБ.");
                await target.WriteAsync(buffer.AsMemory(0, read), cancellationToken);
            }
            if (total == 0) throw new InvalidDataException("Сервер вернул пустой архив.");
            MoveDownloadedArchiveIntoCache(temporaryPath, targetPath);
        }
        finally
        {
            TryDeleteTemporaryFile(temporaryPath);
        }
    }

    private static void MoveDownloadedArchiveIntoCache(string temporaryPath, string targetPath)
    {
        try
        {
            File.Move(temporaryPath, targetPath);
        }
        catch (IOException) when (File.Exists(targetPath) && new FileInfo(targetPath).Length > 0)
        {
            // Another loader instance completed the same immutable package download first.
            TryDeleteTemporaryFile(temporaryPath);
        }
    }

    private static int ExtractArchive(ZipArchive archive, string destinationRoot, List<string> skipped)
    {
        var installed = 0;
        foreach (var entry in archive.Entries)
        {
            var isDirectory = IsDirectory(entry);
            var member = isDirectory ? entry.FullName.TrimEnd('/') : entry.FullName;
            var destination = ResolveEntryPath(destinationRoot, member);
            var relative = Path.GetRelativePath(destinationRoot, destination);
            if (File.Exists(destination) || Directory.Exists(destination))
            {
                skipped.Add(relative);
                continue;
            }
            if (isDirectory)
            {
                Directory.CreateDirectory(destination);
                continue;
            }

            var destinationDirectory = Path.GetDirectoryName(destination)!;
            Directory.CreateDirectory(destinationDirectory);
            var completed = false;
            IOException? lastLockError = null;
            for (var attempt = 0; attempt < 5 && !completed; attempt++)
            {
                var temporaryPath = Path.Combine(destinationDirectory, $".bmrl-{Guid.NewGuid():N}.part");
                try
                {
                    using (var input = entry.Open())
                    using (var output = new FileStream(temporaryPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                        input.CopyTo(output);

                    try
                    {
                        File.Move(temporaryPath, destination);
                        installed++;
                    }
                    catch (IOException) when (File.Exists(destination))
                    {
                        skipped.Add(relative);
                    }
                    completed = true;
                }
                catch (IOException ex) when (IsTransientFileLock(ex))
                {
                    lastLockError = ex;
                    if (attempt < 4) Thread.Sleep(100 * (1 << attempt));
                }
                finally
                {
                    TryDeleteTemporaryFile(temporaryPath);
                }
            }

            if (!completed)
            {
                throw new IOException(
                    $"Не удалось записать файл «{relative}»: он занят другим процессом. Закройте ACC или второй экземпляр загрузчика и повторите установку.",
                    lastLockError);
            }
        }
        return installed;
    }

    private static bool IsTransientFileLock(IOException exception) =>
        OperatingSystem.IsWindows() && (exception.HResult & 0xffff) is 32 or 33;

    private static void TryDeleteTemporaryFile(string path)
    {
        try { if (File.Exists(path)) File.Delete(path); }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }

    private static string ReadSkinFolder(ZipArchiveEntry carEntry)
    {
        using var input = carEntry.Open();
        using var memory = new MemoryStream();
        input.CopyTo(memory);
        if (memory.Length > 5 * 1024 * 1024) throw new InvalidDataException("JSON автомобиля больше 5 МБ.");
        var jsonText = DecodeJson(memory.ToArray());
        using var document = JsonDocument.Parse(jsonText);
        if (!document.RootElement.TryGetProperty("customSkinName", out var value) || value.ValueKind != JsonValueKind.String)
            throw new InvalidDataException("В JSON автомобиля нет строки customSkinName.");
        var name = value.GetString() ?? "";
        if (!IsSafeComponent(name) || !string.Equals(name, name.Trim(), StringComparison.Ordinal))
            throw new InvalidDataException("Имя customSkinName нельзя безопасно использовать как папку ACC.");
        return name;
    }

    private static string DecodeJson(byte[] bytes)
    {
        if (bytes.Length >= 2 && bytes[0] == 0xff && bytes[1] == 0xfe) return Encoding.Unicode.GetString(bytes, 2, bytes.Length - 2);
        if (bytes.Length >= 2 && bytes[0] == 0xfe && bytes[1] == 0xff) return Encoding.BigEndianUnicode.GetString(bytes, 2, bytes.Length - 2);
        if (bytes.Length >= 3 && bytes[0] == 0xef && bytes[1] == 0xbb && bytes[2] == 0xbf) return Encoding.UTF8.GetString(bytes, 3, bytes.Length - 3);
        if (bytes.Length >= 2 && bytes[1] == 0) return Encoding.Unicode.GetString(bytes);
        if (bytes.Length >= 2 && bytes[0] == 0) return Encoding.BigEndianUnicode.GetString(bytes);
        return Encoding.UTF8.GetString(bytes);
    }

    private static void ValidateLiveryMember(string member, string skinFolder)
    {
        var parts = GetSafeEntryParts(member);
        if (parts.Length < 2 || !string.Equals(parts[0], skinFolder, StringComparison.Ordinal))
            throw new InvalidDataException($"Папка в архиве Liveries должна называться точно «{skinFolder}», как в customSkinName.");
    }

    private static string[] GetSafeEntryParts(string entryName)
    {
        var normalized = entryName.Replace('\\', '/');
        if (normalized.StartsWith('/') || Regex.IsMatch(normalized, "^[A-Za-z]:", RegexOptions.CultureInvariant))
            throw new InvalidDataException("Архив содержит абсолютный путь.");
        var parts = normalized.Split('/', StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length == 0 || parts.Any(part => part is "." or ".." || !IsSafeComponent(part)))
            throw new InvalidDataException("Архив содержит небезопасное имя файла.");
        return parts;
    }

    private static string ResolveEntryPath(string root, string entryName)
    {
        var parts = GetSafeEntryParts(entryName);
        var rootPath = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
        var destination = Path.GetFullPath(Path.Combine(rootPath, Path.Combine(parts)));
        if (!destination.StartsWith(rootPath, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Архив пытается записать файл за пределами выбранной папки.");
        return destination;
    }

    private static bool IsSafeComponent(string value)
    {
        if (string.IsNullOrWhiteSpace(value) || value is "." or ".." || value.EndsWith(' ') || value.EndsWith('.')) return false;
        if (value.Any(char.IsControl) || value.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 || value.Contains('/') || value.Contains('\\')) return false;
        var baseName = value.Split('.', 2)[0].ToUpperInvariant();
        return baseName is not ("CON" or "PRN" or "AUX" or "NUL")
            && !Regex.IsMatch(baseName, "^(COM|LPT)[1-9]$", RegexOptions.CultureInvariant);
    }

    private static bool IsDirectory(ZipArchiveEntry entry) => entry.FullName.EndsWith("/", StringComparison.Ordinal);

    private static void ValidateMetadata(LiveryMetadata metadata, int? expectedUserId = null)
    {
        if (metadata.UserId <= 0 || (expectedUserId is not null && metadata.UserId != expectedUserId))
            throw new InvalidDataException("Сервер вернул некорректный ID пилота.");
        if (!Regex.IsMatch(metadata.PackageId ?? "", "^[0-9a-f]{32}$", RegexOptions.CultureInvariant))
            throw new InvalidDataException("Сервер вернул некорректный идентификатор архива.");
        if (string.IsNullOrWhiteSpace(metadata.CarsArchiveUrl) || string.IsNullOrWhiteSpace(metadata.LiveriesArchiveUrl))
            throw new InvalidDataException("В профиле отсутствует один из архивов ливреи.");
        if (metadata.CarsArchiveSize > MaxArchiveBytes || metadata.LiveriesArchiveSize > MaxArchiveBytes)
            throw new InvalidDataException("Архив больше допустимых 500 МБ.");
        _ = ResolveAssetUri(metadata.CarsArchiveUrl);
        _ = ResolveAssetUri(metadata.LiveriesArchiveUrl);
    }

    private static Uri ResolveAssetUri(string path)
    {
        var uri = Uri.TryCreate(path, UriKind.Absolute, out var absolute) && !absolute.IsFile
            ? absolute
            : new Uri(new Uri(WebsiteRoot), path);
        var website = new Uri(WebsiteRoot);
        if (uri.Scheme != Uri.UriSchemeHttps
            || !string.Equals(uri.Host, website.Host, StringComparison.OrdinalIgnoreCase)
            || !uri.IsDefaultPort
            || !uri.AbsolutePath.StartsWith("/api/users/", StringComparison.Ordinal))
            throw new InvalidDataException("Сервер вернул недоверенную ссылку на архив ливреи.");
        return uri;
    }

    private static bool TryParseProfileId(string input, out int userId)
    {
        userId = 0;
        var match = ProfileIdPattern.Match((input ?? "").Trim());
        return match.Success && int.TryParse(match.Groups["id"].Value, out userId) && userId > 0;
    }

    private static void PruneOldCache(string cacheRoot, int userId, string currentPackageId)
    {
        foreach (var directory in Directory.EnumerateDirectories(cacheRoot, $"{userId}-*"))
        {
            if (string.Equals(Path.GetFileName(directory), $"{userId}-{currentPackageId}", StringComparison.OrdinalIgnoreCase)) continue;
            try { Directory.Delete(directory, recursive: true); }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
    }

    private sealed class LiveryMetadata
    {
        [JsonPropertyName("user_id")] public int UserId { get; init; }
        [JsonPropertyName("package_id")] public string? PackageId { get; init; }
        [JsonPropertyName("pilot_name")] public string? PilotName { get; init; }
        [JsonPropertyName("pilot_number")] public int PilotNumber { get; init; }
        [JsonPropertyName("cars_archive_size")] public long CarsArchiveSize { get; init; }
        [JsonPropertyName("cars_archive_url")] public string? CarsArchiveUrl { get; init; }
        [JsonPropertyName("liveries_archive_size")] public long LiveriesArchiveSize { get; init; }
        [JsonPropertyName("liveries_archive_url")] public string? LiveriesArchiveUrl { get; init; }
    }

    private sealed class LoaderVersionManifest
    {
        [JsonPropertyName("version")] public string? Version { get; init; }
        [JsonPropertyName("download_path")] public string? DownloadPath { get; init; }
    }
}
