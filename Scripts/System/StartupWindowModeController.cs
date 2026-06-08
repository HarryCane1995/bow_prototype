using Godot;

public partial class StartupWindowModeController : Node
{
    /// <summary>
    /// Включает применение dev-настроек окна при старте сцены. Если выключено, модуль ничего не меняет.
    /// </summary>
    [ExportGroup("Startup Window Mode")]
    [Export] public bool EnableStartupWindowMode { get; private set; } = true;

    /// <summary>
    /// Если включено, главное окно переносится на primary screen, который возвращает DisplayServer.
    /// </summary>
    [Export] public bool ForcePrimaryScreen { get; private set; } = true;

    /// <summary>
    /// Если включено, главное окно переводится в fullscreen при запуске сцены.
    /// </summary>
    [Export] public bool StartFullscreen { get; private set; } = true;

    /// <summary>
    /// Если включено, используется настоящий exclusive fullscreen. Если выключено, используется обычный fullscreen.
    /// </summary>
    [Export] public bool UseExclusiveFullscreen { get; private set; } = false;

    /// <summary>
    /// Если включено, применение настроек откладывается через CallDeferred, чтобы окно уже было создано.
    /// </summary>
    [Export] public bool ApplyDeferredOnReady { get; private set; } = true;

    /// <summary>
    /// Запускает применение настроек окна при входе контроллера в сцену.
    /// </summary>
    public override void _Ready()
    {
        if (!EnableStartupWindowMode)
        {
            return;
        }

        if (ApplyDeferredOnReady)
        {
            CallDeferred(MethodName.ApplyStartupWindowMode);
            return;
        }

        ApplyStartupWindowMode();
    }

    /// <summary>
    /// Переносит главное окно на primary screen и переводит его в выбранный fullscreen-режим согласно Export-настройкам.
    /// </summary>
    private void ApplyStartupWindowMode()
    {
        if (ForcePrimaryScreen)
        {
            int primaryScreen = DisplayServer.GetPrimaryScreen();
            DisplayServer.WindowSetCurrentScreen(primaryScreen);
        }

        if (!StartFullscreen)
        {
            return;
        }

        DisplayServer.WindowMode fullscreenMode = UseExclusiveFullscreen
            ? DisplayServer.WindowMode.ExclusiveFullscreen
            : DisplayServer.WindowMode.Fullscreen;
        DisplayServer.WindowSetMode(fullscreenMode);
    }
}
