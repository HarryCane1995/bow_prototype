using Godot;

public partial class RuntimeTuningPanel
{
    private VBoxContainer CurrentControlContainer => _currentSectionContent ?? _content;

    private void AddSection(string title, bool expandedByDefault)
    {
        bool expanded = _sectionExpandedStates.TryGetValue(title, out bool savedState)
            ? savedState
            : expandedByDefault;

        CollapsibleSection section = new()
        {
            Name = $"{ToNodeName(title)}Section"
        };
        section.Initialize(title, expanded);
        section.ExpandedChanged += value => _sectionExpandedStates[title] = value;

        _content.AddChild(section);
        _currentSectionContent = section.Content;
    }

    private void AddSubsection(string title)
    {
        Label label = new()
        {
            Name = $"{ToNodeName(title)}Subsection",
            Text = title,
            ThemeTypeVariation = "HeaderSmall"
        };
        CurrentControlContainer.AddChild(label);
    }

    private void AddFloatControl(string labelText, double min, double max, double step, System.Func<float> getter, System.Action<float> setter)
    {
        HBoxContainer row = new()
        {
            Name = $"{ToNodeName(labelText)}Control"
        };
        Label label = new()
        {
            Name = "Label",
            Text = labelText,
            CustomMinimumSize = new Vector2(190.0f, 0.0f)
        };

        HSlider slider = new()
        {
            Name = "Slider",
            MinValue = min,
            MaxValue = max,
            Step = step,
            Value = getter(),
            SizeFlagsHorizontal = Control.SizeFlags.ExpandFill
        };

        SpinBox spinBox = new()
        {
            Name = "SpinBox",
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
        CurrentControlContainer.AddChild(row);
    }

    private void AddBoolControl(string labelText, System.Func<bool> getter, System.Action<bool> setter)
    {
        CheckBox checkBox = new()
        {
            Name = $"{ToNodeName(labelText)}Control",
            Text = labelText,
            ButtonPressed = getter()
        };

        checkBox.Toggled += pressed => setter(pressed);
        CurrentControlContainer.AddChild(checkBox);
    }

    private void AddReadout(string labelText, System.Func<string> getter)
    {
        Label label = new()
        {
            Name = $"{ToNodeName(labelText)}Readout",
            Text = $"{labelText}: {getter()}",
            AutowrapMode = TextServer.AutowrapMode.WordSmart
        };

        _readoutUpdaters.Add(() => label.Text = $"{labelText}: {getter()}");
        CurrentControlContainer.AddChild(label);
    }

    private static string ToNodeName(string text)
    {
        System.Text.StringBuilder builder = new();
        foreach (char character in text)
        {
            if (char.IsLetterOrDigit(character))
            {
                builder.Append(character);
            }
        }

        return builder.Length > 0 ? builder.ToString() : "Control";
    }
}
