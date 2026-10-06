using System.Windows;

namespace BmrlLiveryLoader;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        if (e.Args.Contains("--self-test", StringComparer.OrdinalIgnoreCase))
        {
            try
            {
                var selfTestWindow = new MainWindow();
                selfTestWindow.Close();
                LiveryInstaller.RunSelfTest();
                Shutdown(0);
            }
            catch
            {
                Shutdown(1);
            }
            return;
        }

        var window = new MainWindow();
        MainWindow = window;
        window.Show();
    }
}
