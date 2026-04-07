<!--
  Phase 1 datacard for the X-ray CT block.

  This component is a thin renderer over `props.blockData.xrayct_metadata`,
  which is the JSON dump of the Pydantic `XrayCTMetadata` model. It is
  designed for browseability when many cards are visible at once: a fixed
  preview column on the left, an aligned key/value grid on the right, and
  the URI always visible + copyable in the footer.
-->
<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ blockData: any }>()
const meta = computed(() => props.blockData?.xrayct_metadata ?? null)

const previewUrl = computed(() => {
  // Phase 1: preview is a temp PNG path. Phase 2 will promote this to a
  // datalab File asset and serve via /files/<id>.
  const p = meta.value?.preview_path
  return p ? `/files/raw?path=${encodeURIComponent(p)}` : null
})

const voxel = computed(() => {
  const v = meta.value?.reconstruction?.voxel_size
  return v ? `${v.z} × ${v.y} × ${v.x} ${v.unit}` : '—'
})

const shape = computed(() => {
  const s = meta.value?.reconstruction?.shape
  return s ? `${s.z} × ${s.y} × ${s.x}` : '—'
})

function copyUri() {
  if (meta.value?.asset?.uri) navigator.clipboard.writeText(meta.value.asset.uri)
}
</script>

<template>
  <div v-if="meta" class="xrayct-card">
    <header class="xrayct-card__header">
      <h3>{{ meta.title }}</h3>
      <span class="badge">{{ meta.acquisition.technique }}</span>
    </header>

    <div class="xrayct-card__body">
      <figure class="preview">
        <img v-if="previewUrl" :src="previewUrl" alt="Central slice preview" loading="lazy" />
        <div v-else class="preview--missing">No preview available</div>
        <figcaption v-if="meta.preview_slice_index != null">
          Central slice z = {{ meta.preview_slice_index }}
        </figcaption>
      </figure>

      <dl class="metadata-grid">
        <dt>Beamline</dt>     <dd>{{ meta.acquisition.beamline ?? '—' }}</dd>
        <dt>Energy</dt>       <dd>{{ meta.acquisition.beam_energy_kev ?? '—' }} keV</dd>
        <dt>Exposure</dt>     <dd>{{ meta.acquisition.exposure_time_s ?? '—' }} s</dd>
        <dt>Sample</dt>       <dd>{{ meta.acquisition.sample_name ?? '—' }}</dd>
        <dt>Volume shape</dt> <dd>{{ shape }}</dd>
        <dt>Voxel size</dt>   <dd>{{ voxel }}</dd>
        <dt>Dtype</dt>        <dd>{{ meta.reconstruction.dtype ?? '—' }}</dd>
        <dt>Files</dt>        <dd>{{ meta.asset.n_files ?? 1 }}</dd>
      </dl>
    </div>

    <footer class="xrayct-card__footer">
      <code class="uri" :title="meta.asset.uri">{{ meta.asset.uri }}</code>
      <button @click="copyUri">Copy URI</button>
      <span class="scheme">{{ meta.asset.scheme }}</span>
    </footer>
  </div>
</template>

<style scoped>
.xrayct-card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; font-family: system-ui; }
.xrayct-card__header { display: flex; justify-content: space-between; align-items: center; }
.badge { background: #eef; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
.xrayct-card__body { display: grid; grid-template-columns: 240px 1fr; gap: 1rem; margin-top: .75rem; }
.preview img { width: 100%; border-radius: 4px; background: #000; }
.preview--missing { aspect-ratio: 1; display: grid; place-items: center; background: #f4f4f4; color: #888; border-radius: 4px; }
.metadata-grid { display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; font-size: 0.9em; margin: 0; }
.metadata-grid dt { color: #666; }
.metadata-grid dd { margin: 0; font-variant-numeric: tabular-nums; }
.xrayct-card__footer { display: flex; gap: .5rem; align-items: center; margin-top: 1rem; padding-top: .5rem; border-top: 1px dashed #ddd; }
.uri { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.8em; background: #f6f6f6; padding: 4px 6px; border-radius: 4px; }
.scheme { font-size: 0.75em; text-transform: uppercase; color: #888; }
</style>
