using Godot;

[GlobalClass]
public partial class GameplayAudioSettings : Resource
{
    [ExportGroup("Mix (linear gain)")]
    [Export(PropertyHint.Range, "0,1.5,0.01")] public float Sfx { get; set; } = 1f;
    [Export(PropertyHint.Range, "0,1.5,0.01")] public float Movement { get; set; } = 1f;
    [Export(PropertyHint.Range, "0,1.5,0.01")] public float Grapple { get; set; } = 1f;
    [Export(PropertyHint.Range, "0,1.5,0.01")] public float System { get; set; } = 1f;
    [Export(PropertyHint.Range, "0,1.5,0.01")] public float Speed { get; set; } = 1f;
    [Export(PropertyHint.Range, "0,1.5,0.01")] public float Landing { get; set; } = 1f;
    [Export(PropertyHint.Range, "0,1.5,0.01")] public float Slide { get; set; } = 1f;
    [Export(PropertyHint.Range, "0,1.5,0.01")] public float Wallrun { get; set; } = 1f;
    [Export] public bool Muted { get; set; }
    [ExportGroup("Speed response")]
    [Export(PropertyHint.Range, "0,30,0.5,suffix:m/s")] public float WindThreshold { get; set; } = 9f;
    [Export(PropertyHint.Range, "15,100,0.5,suffix:m/s")] public float WindFullSpeed { get; set; } = 44f;
    [Export(PropertyHint.Range, "1,25,0.5,suffix:1/s")] public float WindResponse { get; set; } = 8f;
    [ExportGroup("Impact and variation")]
    [Export(PropertyHint.Range, "0.5,8,0.1,suffix:m/s")] public float LandingThreshold { get; set; } = 2.5f;
    [Export(PropertyHint.Range, "0,0.12,0.005")] public float PitchVariance { get; set; } = .035f;
}
