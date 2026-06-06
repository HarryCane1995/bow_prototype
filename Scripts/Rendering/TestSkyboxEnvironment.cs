using Godot;

[Tool]
public partial class TestSkyboxEnvironment : WorldEnvironment
{
    [Export(PropertyHint.File, "*.hdr,*.exr,*.png,*.jpg,*.jpeg")]
    public string SkyTexturePath = "res://Art/Skyboxes/ferndale_studio_10_4k.exr";

    [Export] public float BackgroundEnergy = 2.39f;
    [Export] public float SkyEnergy = 1.0f;
    [Export] public float AmbientLightEnergy = 3.62f;

    [Export] public bool GaussianBlurEnabled = false;

    [Export(PropertyHint.Range, "0,32,1")]
    public int GaussianBlurRadius = 0;

    [Export(PropertyHint.Range, "0.1,32.0,0.1")]
    public float GaussianBlurSigma = 4.0f;

    [Export(PropertyHint.Range, "256,4096,1")]
    public int GaussianBlurMaxSize = 2048;

    public override void _Ready()
    {
        ApplySkybox();
    }

    private void ApplySkybox()
    {
        if (string.IsNullOrWhiteSpace(SkyTexturePath))
        {
            GD.PushWarning("SkyTexturePath is empty.");
            return;
        }

        var panoramaTexture = ResourceLoader.Load<Texture2D>(SkyTexturePath);

        if (panoramaTexture == null)
        {
            GD.PushWarning($"Could not load sky texture at path: {SkyTexturePath}");
            return;
        }

        var skyTexture = CreateSkyTexture(panoramaTexture);

        var panoramaMaterial = new PanoramaSkyMaterial
        {
            Panorama = skyTexture,
            EnergyMultiplier = SkyEnergy
        };

        var sky = new Sky
        {
            SkyMaterial = panoramaMaterial
        };

        var environment = Environment ?? new Godot.Environment();

        environment.BackgroundMode = Godot.Environment.BGMode.Sky;
        environment.Sky = sky;
        environment.BackgroundEnergyMultiplier = BackgroundEnergy;
        environment.AmbientLightSource = Godot.Environment.AmbientSource.Sky;
        environment.AmbientLightEnergy = AmbientLightEnergy;
        environment.ReflectedLightSource = Godot.Environment.ReflectionSource.Sky;

        Environment = environment;
    }

    private Texture2D CreateSkyTexture(Texture2D sourceTexture)
    {
        var blurRadius = Mathf.Clamp(GaussianBlurRadius, 0, 32);
        var blurSigma = Mathf.Max(0.1f, GaussianBlurSigma);

        if (!GaussianBlurEnabled || blurRadius <= 0)
        {
            return sourceTexture;
        }

        var sourceImage = sourceTexture.GetImage();

        if (sourceImage == null)
        {
            GD.PushWarning($"Could not read sky texture image data for Gaussian blur: {SkyTexturePath}");
            return sourceTexture;
        }

        if (sourceImage.IsCompressed() && sourceImage.Decompress() != Error.Ok)
        {
            GD.PushWarning($"Could not decompress sky texture for Gaussian blur: {SkyTexturePath}");
            return sourceTexture;
        }

        var maxSize = Mathf.Max(256, GaussianBlurMaxSize);
        var width = sourceImage.GetWidth();
        var height = sourceImage.GetHeight();

        if (width > maxSize || height > maxSize)
        {
            var scale = Mathf.Min((float)maxSize / width, (float)maxSize / height);
            var resizedWidth = Mathf.Max(1, Mathf.RoundToInt(width * scale));
            var resizedHeight = Mathf.Max(1, Mathf.RoundToInt(height * scale));

            sourceImage.Resize(resizedWidth, resizedHeight, Image.Interpolation.Lanczos);
        }

        var blurredImage = ApplyGaussianBlur(sourceImage, blurRadius, blurSigma);
        return ImageTexture.CreateFromImage(blurredImage);
    }

    private static Image ApplyGaussianBlur(Image sourceImage, int radius, float sigma)
    {
        var kernel = CreateGaussianKernel(radius, sigma);
        var width = sourceImage.GetWidth();
        var height = sourceImage.GetHeight();
        var format = sourceImage.GetFormat();
        var horizontalPass = Image.CreateEmpty(width, height, false, format);
        var blurredImage = Image.CreateEmpty(width, height, false, format);

        for (var y = 0; y < height; y++)
        {
            for (var x = 0; x < width; x++)
            {
                var color = new Color(0, 0, 0, 0);

                for (var offset = -radius; offset <= radius; offset++)
                {
                    var sampleX = PositiveModulo(x + offset, width);
                    color += sourceImage.GetPixel(sampleX, y) * kernel[offset + radius];
                }

                horizontalPass.SetPixel(x, y, color);
            }
        }

        for (var y = 0; y < height; y++)
        {
            for (var x = 0; x < width; x++)
            {
                var color = new Color(0, 0, 0, 0);

                for (var offset = -radius; offset <= radius; offset++)
                {
                    var sampleY = Mathf.Clamp(y + offset, 0, height - 1);
                    color += horizontalPass.GetPixel(x, sampleY) * kernel[offset + radius];
                }

                blurredImage.SetPixel(x, y, color);
            }
        }

        return blurredImage;
    }

    private static float[] CreateGaussianKernel(int radius, float sigma)
    {
        var kernel = new float[(radius * 2) + 1];
        var sigmaSquared = sigma * sigma;
        var sum = 0.0f;

        for (var offset = -radius; offset <= radius; offset++)
        {
            var value = Mathf.Exp(-(offset * offset) / (2.0f * sigmaSquared));
            kernel[offset + radius] = value;
            sum += value;
        }

        for (var i = 0; i < kernel.Length; i++)
        {
            kernel[i] /= sum;
        }

        return kernel;
    }

    private static int PositiveModulo(int value, int modulo)
    {
        return ((value % modulo) + modulo) % modulo;
    }
}
