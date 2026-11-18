import test from 'node:test';
import assert from 'node:assert/strict';
import {
  countActiveSearchFilters,
  hasActiveSearchFilters,
  sanitizeSearchFilters,
  toggleFavoriteFilter,
} from '../../src/utils/searchFilters.ts';

function resolvePhotoGalleryEndpoint(query, filters) {
  const hasFilters = hasActiveSearchFilters(filters);
  const hasQuery = Boolean(query && query.trim() !== '');
  return hasQuery || hasFilters ? 'searchPhotos' : 'fetchPhotos';
}

test('TC-SRC-12.1: toggleFavoriteFilter toggles is_favorite ON and completely removes key on OFF', () => {
  assert.deepEqual(toggleFavoriteFilter(undefined), { is_favorite: true });
  assert.deepEqual(toggleFavoriteFilter({ is_favorite: false }), { is_favorite: true });

  const enabled = toggleFavoriteFilter({});
  assert.deepEqual(enabled, { is_favorite: true });
  assert.equal('is_favorite' in enabled, true);
  assert.equal(Object.keys(enabled).length, 1);

  const disabled = toggleFavoriteFilter(enabled);
  assert.deepEqual(disabled, {});
  assert.equal('is_favorite' in disabled, false);
  assert.equal(Object.keys(disabled).length, 0);
  assert.equal(countActiveSearchFilters(disabled), 0);
  assert.equal(hasActiveSearchFilters(disabled), false);
});

test('TC-SRC-12.2: toggleFavoriteFilter preserves other active filters and drops stale undefined keys', () => {
  const combined = toggleFavoriteFilter({
    camera_model: 'ILCE-7M4',
    lens_model: '',
    iso_min: Number.NaN,
  });
  assert.deepEqual(combined, {
    camera_model: 'ILCE-7M4',
    is_favorite: true,
  });

  const withoutFavorite = toggleFavoriteFilter(combined);
  assert.deepEqual(withoutFavorite, {
    camera_model: 'ILCE-7M4',
  });
  assert.equal('is_favorite' in withoutFavorite, false);
  assert.equal(countActiveSearchFilters(withoutFavorite), 1);
  assert.equal(hasActiveSearchFilters(withoutFavorite), true);
});

test('TC-SRC-12.3: sanitizeSearchFilters strips undefined, null, empty/whitespace strings, and non-finite numbers while keeping 0 and booleans', () => {
  assert.deepEqual(sanitizeSearchFilters(undefined), {});
  assert.deepEqual(sanitizeSearchFilters(null), {});

  const sanitized = sanitizeSearchFilters({
    is_favorite: undefined,
    camera_model: '   ',
    lens_model: '',
    iso_min: 0,
    iso_max: Number.NaN,
    f_number_min: Number.POSITIVE_INFINITY,
    focal_length_min: 35,
    date_from: undefined,
  });

  assert.deepEqual(sanitized, {
    iso_min: 0,
    focal_length_min: 35,
  });
  assert.equal('is_favorite' in sanitized, false);
  assert.equal(countActiveSearchFilters(sanitized), 2);
});

test('TC-SRC-12.4: countActiveSearchFilters and hasActiveSearchFilters ignore polluted undefined keys to prevent phantom badge and fetchPhotos misrouting', () => {
  const pollutedFilters = {
    is_favorite: undefined,
    camera_model: '',
    iso_min: Number.NaN,
  };

  assert.equal(countActiveSearchFilters(pollutedFilters), 0);
  assert.equal(hasActiveSearchFilters(pollutedFilters), false);
  assert.equal(resolvePhotoGalleryEndpoint('', pollutedFilters), 'fetchPhotos');
  assert.equal(resolvePhotoGalleryEndpoint('   ', pollutedFilters), 'fetchPhotos');
  assert.equal(resolvePhotoGalleryEndpoint('', { is_favorite: true }), 'searchPhotos');
  assert.equal(resolvePhotoGalleryEndpoint('sunset', pollutedFilters), 'searchPhotos');
});
