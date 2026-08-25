/// <reference types="vite/client" />

import { parseSiteManifest, type SiteManifest } from './siteManifest';

import index from './generated/index.json';
import emberStudio from './generated/ember-studio.json';
import northstarLibrary from './generated/northstar-library.json';

const profiles: Record<string, unknown> = {
  'ember-studio': emberStudio,
  'northstar-library': northstarLibrary,
};

export function selectSiteManifest(profileId?: string): SiteManifest {
  const selected = profileId || import.meta.env.VITE_SITE_PROFILE || index.defaultProfile;
  if (!Object.prototype.hasOwnProperty.call(index.profiles, selected) || !(selected in profiles)) {
    throw new Error('VITE_SITE_PROFILE is not an allowed generated profile');
  }
  return parseSiteManifest(profiles[selected]);
}

export const siteManifest = selectSiteManifest();
