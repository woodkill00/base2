/// <reference types="vite/client" />

import { parseSiteManifest, type SiteManifest } from './siteManifest';

import { index, profiles } from './generated/siteRegistry';

export function selectSiteManifest(profileId?: string): SiteManifest {
  const selected = profileId || import.meta.env.VITE_SITE_PROFILE || index.defaultProfile;
  if (!Object.prototype.hasOwnProperty.call(index.profiles, selected) || !(selected in profiles)) {
    throw new Error('VITE_SITE_PROFILE is not an allowed generated profile');
  }
  return parseSiteManifest(profiles[selected]);
}

export const siteManifest = selectSiteManifest();
