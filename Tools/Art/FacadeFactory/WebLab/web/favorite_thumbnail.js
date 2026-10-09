import { FacadeViewer } from './facade_viewer.js?v=0.4';

// Render only when starring a recipe. Isolated textures prevent edits, orbiting,
// debug maps, and disposal of the live preview from changing this snapshot.
export async function renderFavoriteThumbnail(snapshot) {
  const host = document.createElement('div');
  host.className = 'favorite-thumbnail-renderer';
  host.setAttribute('aria-hidden', 'true');
  document.body.append(host);
  let preview;
  try {
    preview = new FacadeViewer(host);
    preview.renderer.setAnimationLoop(null);
    preview.controls.enabled = false;
    preview.renderer.setPixelRatio(1);
    preview.resize();
    const mode = snapshot.recipe.surface_mode;
    preview.setShape(mode === 'UNIQUE_FACADE' ? 'BOX' : mode === 'TILEABLE_SURFACE' ? 'FLOOR_PATCH' : 'CYLINDER');
    const repeat = mode === 'TILEABLE_SURFACE' ? 3 * snapshot.recipe.parameters.tile_scale : 1;
    preview.setOptions({map: 'material', uvX: repeat, uvY: repeat, breakupOn: true,
      emissionOn: true, emissionStrength: snapshot.recipe.parameters.emission_strength ?? 1.15});
    preview.show(await preview.prepareMaps(snapshot));
    preview.renderer.render(preview.scene, preview.camera);
    // PNG transport avoids a second lossy encode. The server stores a small WebP.
    return preview.renderer.domElement.toDataURL('image/png');
  } finally {
    preview?.dispose();
    host.remove();
  }
}
