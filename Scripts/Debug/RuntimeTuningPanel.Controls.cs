using Godot;

public partial class RuntimeTuningPanel
{
    private void AddSection(string title)
    {
        Label label = new()
        {
            Text = title,
            ThemeTypeVariation = "HeaderSmall"
        };
        _content.AddChild(label);
    }

    private void AddFloatControl(string labelText, double min, double max, double step, System.Func<float> getter, System.Action<float> setter)
    {
        HBoxContainer row = new();
        Label label = new()
        {
            Text = labelText,
            CustomMinimumSize = new Vector2(190.0f, 0.0f)
        };

        HSlider slider = new()
        {
            MinValue = min,
            MaxValue = max,
            Step = step,
            Value = getter(),
            SizeFlagsHorizontal = Control.SizeFlags.ExpandFill
        };

        SpinBox spinBox = new()
        {
            MinValue = min,
            MaxValue = max,
            Step = step,
            Value = getter(),
            CustomMinimumSize = new Vector2(95.0f, 0.0f)
        };

        slider.ValueChanged += value =>
        {
            setter((float)value);
            spinBox.SetValueNoSignal(value);
        };

        spinBox.ValueChanged += value =>
        {
            setter((float)value);
            slider.SetValueNoSignal(value);
        };

        row.AddChild(label);
        row.AddChild(slider);
        row.AddChild(spinBox);
        _content.AddChild(row);
    }

    private void AddBoolControl(string labelText, System.Func<bool> getter, System.Action<bool> setter)
    {
        CheckBox checkBox = new()
        {
            Text = labelText,
            ButtonPressed = getter()
        };

        checkBox.Toggled += pressed => setter(pressed);
        _content.AddChild(checkBox);
    }

    private void AddReadout(string labelText, System.Func<string> getter)
    {
        Label label = new()
        {
            Text = $"{labelText}: {getter()}",
            AutowrapMode = TextServer.AutowrapMode.WordSmart
        };

        _readoutUpdaters.Add(() => label.Text = $"{labelText}: {getter()}");
        _content.AddChild(label);
    }
}
