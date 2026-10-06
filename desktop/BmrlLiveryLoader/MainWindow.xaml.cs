using Microsoft.Win32;
using System.Diagnostics;
using System.IO;
using System.Windows;

namespace BmrlLiveryLoader;

public partial class MainWindow : Window
{
    private Uri? _updateDownloadUri;

    public MainWindow()
    {
        InitializeComponent();
        DetectAccFolders();
    }

    private void DetectFolders_Click(object sender, RoutedEventArgs e) => DetectAccFolders();

    private void BrowseCars_Click(object sender, RoutedEventArgs e) => ChooseFolder(CarsFolderInput, "Выберите папку Cars");

    private void BrowseLiveries_Click(object sender, RoutedEventArgs e) => ChooseFolder(LiveriesFolderInput, "Выберите папку Liveries");

    private void DetectAccFolders()
    {
        var customs = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "Assetto Corsa Competizione", "Customs");
        var cars = Path.Combine(customs, "Cars");
        var liveries = Path.Combine(customs, "Liveries");
        if (Directory.Exists(cars)) CarsFolderInput.Text = cars;
        if (Directory.Exists(liveries)) LiveriesFolderInput.Text = liveries;
    }

    private void ChooseFolder(System.Windows.Controls.TextBox target, string title)
    {
        var dialog = new OpenFolderDialog
        {
            Title = title,
            Multiselect = false,
            InitialDirectory = Directory.Exists(target.Text)
                ? target.Text
                : Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)
        };
        if (dialog.ShowDialog(this) == true) target.Text = dialog.FolderName;
    }

    private async void Window_Loaded(object sender, RoutedEventArgs e)
    {
        try
        {
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
            var update = await LiveryInstaller.CheckForUpdateAsync(timeout.Token);
            if (update is null) return;

            _updateDownloadUri = update.DownloadUri;
            UpdateVersionText.Text = $"Доступна новая версия загрузчика · {update.Version}";
            UpdateNoticePanel.Visibility = Visibility.Visible;
        }
        catch
        {
            // Version checks are best-effort; the livery installer remains usable offline.
        }
    }

    private void DownloadUpdate_Click(object sender, RoutedEventArgs e)
    {
        if (_updateDownloadUri is null) return;
        try
        {
            Process.Start(new ProcessStartInfo(_updateDownloadUri.AbsoluteUri) { UseShellExecute = true });
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, $"Не удалось открыть загрузку обновления: {ex.Message}", "BMRL · Загрузчик ливрей", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private async void Install_Click(object sender, RoutedEventArgs e) => await InstallAsync(installAll: false);

    private async void InstallAll_Click(object sender, RoutedEventArgs e) => await InstallAsync(installAll: true);

    private async Task InstallAsync(bool installAll)
    {
        InstallButton.IsEnabled = false;
        InstallAllButton.IsEnabled = false;
        ConflictsText.Visibility = Visibility.Collapsed;
        ConflictsText.Text = string.Empty;
        DetailsText.Text = string.Empty;
        StatusText.Text = "Проверяю папки и профиль…";
        try
        {
            var progress = new Progress<string>(message => StatusText.Text = message);
            if (installAll)
            {
                var result = await LiveryInstaller.InstallAllAsync(
                    CarsFolderInput.Text,
                    LiveriesFolderInput.Text,
                    progress);
                if (result.TotalLiveries == 0)
                {
                    StatusText.Text = "В каталоге пока нет ливрей";
                    DetailsText.Text = "Когда пилоты опубликуют ливреи на BMRL, их можно будет установить отсюда одним нажатием.";
                    return;
                }

                StatusText.Text = result.FailedLiveries.Count == 0
                    ? "Установка каталога завершена"
                    : "Установка каталога завершена не полностью";
                DetailsText.Text = $"Успешно: {result.SuccessfulLiveries} из {result.TotalLiveries}. Добавлено файлов: {result.InstalledFiles}. Уже существовало: {result.SkippedFiles.Count}.";
                var details = result.FailedLiveries.Concat(result.SkippedFiles).ToArray();
                if (details.Length > 0)
                {
                    const int maxVisibleDetails = 120;
                    var visible = details.Take(maxVisibleDetails).ToList();
                    if (details.Length > visible.Count)
                        visible.Add($"… и ещё {details.Length - visible.Count} строк.");
                    ConflictsText.Text = string.Join(Environment.NewLine, visible);
                    ConflictsText.Visibility = Visibility.Visible;
                }
                return;
            }

            var singleResult = await LiveryInstaller.InstallAsync(
                ProfileInput.Text,
                CarsFolderInput.Text,
                LiveriesFolderInput.Text,
                progress);
            StatusText.Text = "Установка завершена";
            DetailsText.Text = $"Папка ливреи: {singleResult.SkinFolder}. Добавлено файлов: {singleResult.InstalledFiles}. Пропущено из-за совпадений: {singleResult.SkippedFiles.Count}.";
            if (singleResult.SkippedFiles.Count > 0)
            {
                ConflictsText.Text = string.Join(Environment.NewLine, singleResult.SkippedFiles.Take(120));
                ConflictsText.Visibility = Visibility.Visible;
            }
        }
        catch (Exception ex)
        {
            StatusText.Text = "Не удалось установить ливрею";
            DetailsText.Text = ex.Message;
        }
        finally
        {
            InstallButton.IsEnabled = true;
            InstallAllButton.IsEnabled = true;
        }
    }
}
