import type { ArtStyle, StyleProfile } from '../types';

export const artStyleLabels: Record<ArtStyle | string, string> = {
  pixel: '像素风',
  hand_drawn: '手绘风',
  cartoon: '卡通风',
  realistic: '写实风',
  custom: '自定义',
};

export const perspectiveLabels: Record<string, string> = {
  top_down: '俯视',
  side_scroller: '横版',
  isometric: '等距',
};

function isCanonicalPreset(style: StyleProfile): boolean {
  return style.name === getStyleDisplayName(style);
}

export function getStyleDisplayName(style: StyleProfile): string {
  return style.is_preset
    ? artStyleLabels[style.art_style] ?? style.name
    : style.name;
}

export function compactStyleOptions(styles: StyleProfile[]): StyleProfile[] {
  const bestPresetByStyle = new Map<ArtStyle, StyleProfile>();

  styles.forEach((style) => {
    if (!style.is_preset) return;
    const existing = bestPresetByStyle.get(style.art_style);
    if (!existing || (!isCanonicalPreset(existing) && isCanonicalPreset(style))) {
      bestPresetByStyle.set(style.art_style, style);
    }
  });

  const emittedPresetStyles = new Set<ArtStyle>();
  return styles.filter((style) => {
    if (!style.is_preset) return true;
    const chosen = bestPresetByStyle.get(style.art_style);
    if (style.id !== chosen?.id || emittedPresetStyles.has(style.art_style)) {
      return false;
    }
    emittedPresetStyles.add(style.art_style);
    return true;
  });
}
