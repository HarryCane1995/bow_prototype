using Godot;
using System;

public partial class PlayerAudioController
{
    private Window _panel;
    private Label _meter;
    private CheckButton _muteButton;
    private Input.MouseModeEnum _previousMouseMode;
    private const string SavePath = "user://procedural_audio_settings.tres";

    private void InitializePanel()
    {
        if (ResourceLoader.Exists(SavePath)) Settings = GD.Load<GameplayAudioSettings>(SavePath) ?? Settings;
        _panel = new Window { Title = "PROCEDURAL AUDIO — F6 close", Size = new Vector2I(430, 640), Visible = false };
        _panel.CloseRequested += ClosePanel;
        _panel.WindowInput += HandlePanelInput;
        AddChild(_panel);
        var scroll = new ScrollContainer(); scroll.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        _panel.AddChild(scroll);
        var content = new VBoxContainer { SizeFlagsHorizontal = Control.SizeFlags.ExpandFill };
        scroll.AddChild(content);
        content.AddChild(new Label { Text = "AUDIO  |  F6 panel  |  F7 mute\nSettings affect audio only. R/F1 retain the mix." });
        _meter = new Label(); content.AddChild(_meter);
        _muteButton = new CheckButton { Text = "Mute SFX", ButtonPressed = Settings.Muted };
        _muteButton.Toggled += value => Settings.Muted = value; content.AddChild(_muteButton);
        var solo = new OptionButton();
        foreach (string family in new[] { "All", "Movement", "Grapple", "System", "Speed" }) solo.AddItem(family);
        solo.ItemSelected += index => _solo = solo.GetItemText((int)index);
        content.AddChild(new Label { Text = "Solo bus" }); content.AddChild(solo);
        AddSlider(content, "SFX", () => Settings.Sfx, v => Settings.Sfx=v);
        AddSlider(content, "Movement", () => Settings.Movement, v => Settings.Movement=v);
        AddSlider(content, "Grapple", () => Settings.Grapple, v => Settings.Grapple=v);
        AddSlider(content, "System", () => Settings.System, v => Settings.System=v);
        AddSlider(content, "Speed / wind", () => Settings.Speed, v => Settings.Speed=v);
        AddSlider(content, "Landings", () => Settings.Landing, v => Settings.Landing=v);
        AddSlider(content, "Slide", () => Settings.Slide, v => Settings.Slide=v);
        AddSlider(content, "Wallrun", () => Settings.Wallrun, v => Settings.Wallrun=v);
        AddSlider(content, "Wind threshold (m/s)", () => Settings.WindThreshold, v => Settings.WindThreshold=v, 0,30,.5);
        AddSlider(content, "Wind full speed (m/s)", () => Settings.WindFullSpeed, v => Settings.WindFullSpeed=v, 15,100,.5);
        AddSlider(content, "Wind response (1/s)", () => Settings.WindResponse, v => Settings.WindResponse=v, 1,25,.5);
        AddSlider(content, "Pitch variance", () => Settings.PitchVariance, v => Settings.PitchVariance=v, 0,.12,.005);
        var save = new Button { Text = "Save audio mix (user data only)" };
        save.Pressed += () => { var error = ResourceSaver.Save(Settings, SavePath); _meter.Text = $"Audio save: {error}"; };
        content.AddChild(save);
    }

    private static void AddSlider(VBoxContainer content, string name, Func<float> get, Action<float> set,
        double min=0, double max=1.5, double step=.01)
    {
        var row = new HBoxContainer();
        var label = new Label { Text = $"{name}: {get():0.###}", CustomMinimumSize = new Vector2(225,0) };
        var slider = new HSlider { MinValue=min, MaxValue=max, Step=step, Value=get(), SizeFlagsHorizontal=Control.SizeFlags.ExpandFill };
        slider.ValueChanged += value => { set((float)value); label.Text=$"{name}: {value:0.###}"; };
        row.AddChild(label); row.AddChild(slider); content.AddChild(row);
    }

    public override void _Input(InputEvent @event)
    {
        if (@event is not InputEventKey key || !key.Pressed || key.Echo) return;
        if (key.Keycode == Key.F7) { Settings.Muted = !Settings.Muted; GetViewport().SetInputAsHandled(); }
        if (key.Keycode != Key.F6) return;
        if (_panel.Visible) ClosePanel();
        else
        {
            _previousMouseMode = Input.MouseMode;
            Input.MouseMode = Input.MouseModeEnum.Visible;
            _panel.PopupCentered();
        }
        GetViewport().SetInputAsHandled();
    }

    private void ClosePanel()
    {
        _panel.Hide();
        Input.MouseMode = _previousMouseMode;
    }

    private void HandlePanelInput(InputEvent @event)
    {
        if (@event is not InputEventKey key || !key.Pressed || key.Echo) return;
        // A native Window has its own Viewport: its hotkeys do not necessarily
        // reach the autoload's root-viewport _Input callback.
        if (key.Keycode == Key.F6) { ClosePanel(); _panel.SetInputAsHandled(); }
        if (key.Keycode == Key.F7) { Settings.Muted = !Settings.Muted; _panel.SetInputAsHandled(); }
    }

    public override void _Process(double delta)
    {
        if (_panel?.Visible != true) return;
        _muteButton.SetPressedNoSignal(Settings.Muted);
        float speed = IsInstanceValid(_player) ? Horizontal(_player.Velocity) : 0;
        _meter.Text = $"Horizontal {speed:0.0} m/s | wind {_wind:0.00} | voices {ActiveVoices()}/12";
    }
}
