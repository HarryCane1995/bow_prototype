using Godot;
using System;
using System.Collections.Generic;

public partial class PlayerAudioController
{
    private const string Bank = "res://Assets/Audio/Procedural/";
    private readonly Random _random = new(0xB07A);
    private readonly Dictionary<string, AudioStreamWav[]> _sounds = new();
    private readonly Dictionary<string, int> _lastVariant = new();
    private readonly Dictionary<string, double> _lastPlayed = new();
    private readonly List<AudioStreamPlayer> _voices = new();
    private readonly Dictionary<string, AudioStreamPlayer> _loops = new();
    private readonly Dictionary<string, float> _loopGains = new();
    private readonly Dictionary<string, float> _busGains = new();
    private string _solo = "All";

    private void InitializePlayback()
    {
        // Assets are cached once, never loaded from the gameplay hot path.
        foreach (var family in new Dictionary<string, int> {
            ["jump"]=3, ["air_jump"]=3, ["landing_light"]=3, ["landing_medium"]=3,
            ["landing_heavy"]=3, ["wall_enter"]=2, ["wall_exit"]=2, ["wall_jump"]=3,
            ["slide_enter"]=3, ["slide_exit"]=2, ["grapple_fire"]=3, ["grapple_attach"]=3,
            ["grapple_release"]=3, ["checkpoint"]=2, ["reset"]=2 })
        {
            var variants = new AudioStreamWav[family.Value];
            for (int i = 0; i < variants.Length; i++) variants[i] = GD.Load<AudioStreamWav>($"{Bank}{family.Key}_{i}.wav");
            _sounds[family.Key] = variants;
        }
        for (int i = 0; i < 12; i++)
        {
            var voice = new AudioStreamPlayer { Name = $"OneShot{i}" };
            AddChild(voice); _voices.Add(voice);
        }
        foreach (string name in new[] { "wind_low", "wind_high", "slide_loop", "wall_loop", "grapple_loop" })
        {
            var stream = (AudioStreamWav)GD.Load<AudioStreamWav>($"{Bank}{name}.wav").Duplicate();
            stream.LoopMode = AudioStreamWav.LoopModeEnum.Forward;
            stream.LoopBegin = 0; stream.LoopEnd = (int)Math.Round(stream.GetLength() * stream.MixRate);
            var voice = new AudioStreamPlayer { Name = name, Stream = stream, VolumeDb = -80,
                Bus = name.StartsWith("wind") ? "Speed" : name.StartsWith("grapple") ? "Grapple" : "Movement" };
            AddChild(voice); _loops[name] = voice; _loopGains[name] = 0;
        }
    }

    private void OneShot(string family, string bus, float db, float gain = 1, float pitch = 1)
    {
        if (gain <= 0 || (_lastPlayed.TryGetValue(family, out double previous) && _time - previous < .055)) return;
        _lastPlayed[family] = _time;
        var variants = _sounds[family];
        int index = _random.Next(variants.Length);
        if (_lastVariant.TryGetValue(family, out int last) && index == last) index = (index + 1) % variants.Length;
        _lastVariant[family] = index;
        // Bounded pool; never cut a live transient to allocate a new voice.
        AudioStreamPlayer voice = _voices.Find(v => !v.Playing);
        if (voice == null) { Trace("voice_budget_drop", new() { ["family"] = family }); return; }
        voice.Stream = variants[index]; voice.Bus = bus;
        float pitchOffset = ((float)_random.NextDouble() * 2 - 1) * Settings.PitchVariance;
        voice.PitchScale = pitch * (1 + pitchOffset);
        voice.VolumeDb = db + Mathf.LinearToDb(Mathf.Max(.0001f, gain)) + ((float)_random.NextDouble() * 1.2f - .6f);
        voice.Play();
        _duck = .13f;
        Trace("one_shot", new() { ["family"] = family, ["variant"] = index,
            ["pitch"] = voice.PitchScale, ["gain_db"] = voice.VolumeDb });
    }

    private void SetLoop(string name, float target, float pitch, float delta)
    {
        var voice = _loops[name];
        float gain = Mathf.Lerp(_loopGains[name], target, 1 - Mathf.Exp(-18 * delta));
        _loopGains[name] = gain;
        if (gain < .00015f && target < .00015f) { voice.Stop(); _loopGains[name] = 0; return; }
        voice.VolumeDb = Mathf.LinearToDb(Mathf.Max(.0001f, gain));
        voice.PitchScale = Mathf.Lerp(voice.PitchScale, pitch, 1 - Mathf.Exp(-8 * delta));
        if (!voice.Playing) voice.Play();
    }

    private void ApplyMix(float delta)
    {
        SetBus("SFX", Settings.Muted ? 0 : Settings.Sfx, delta, -3);
        SetBus("Movement", Settings.Movement * SoloGain("Movement"), delta);
        SetBus("Grapple", Settings.Grapple * SoloGain("Grapple"), delta);
        SetBus("System", Settings.System * SoloGain("System"), delta);
        SetBus("Speed", Settings.Speed * SoloGain("Speed"), delta);
    }

    private float SoloGain(string bus) => _solo == "All" || _solo == bus ? 1 : 0;

    private void SetBus(string bus, float target, float delta, float baseDb = 0)
    {
        float gain = Mathf.Lerp(_busGains.GetValueOrDefault(bus, 1), target, 1 - Mathf.Exp(-25 * delta));
        _busGains[bus] = gain;
        AudioServer.SetBusVolumeDb(AudioServer.GetBusIndex(bus), baseDb + Mathf.LinearToDb(Mathf.Max(.0001f, gain)));
    }

    private int ActiveVoices() => _voices.FindAll(v => v.Playing).Count;
    private Godot.Collections.Dictionary LoopSnapshot()
    {
        var result = new Godot.Collections.Dictionary();
        foreach (var loop in _loops) result[loop.Key] = new Godot.Collections.Dictionary {
            ["playing"] = loop.Value.Playing, ["gain"] = _loopGains[loop.Key] };
        return result;
    }
}
