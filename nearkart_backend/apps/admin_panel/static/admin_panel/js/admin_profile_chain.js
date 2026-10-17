/**
 * Nearspot — Chained Location Selects for AdminProfile
 *
 * Hierarchy: State → District → City → Area
 * Each dropdown is populated via AJAX based on the parent selection.
 * URL: /admin/admin_panel/adminprofile/location-options/?field=district&state=...
 */
(function ($) {
  'use strict';

  const BASE_URL = (window.location_options_url) ||
                   '/admin/admin_panel/adminprofile/location-options/';

  function buildSelect(values, placeholder) {
    const opts = ['<option value="">' + placeholder + '</option>'];
    values.forEach(function (v) {
      opts.push('<option value="' + v + '">' + v + '</option>');
    });
    return opts.join('');
  }

  function resetSelect($el, placeholder) {
    $el.html('<option value="">' + placeholder + '</option>').val('').prop('disabled', true);
  }

  function loadOptions(field, params, $target, placeholder, currentValue, callback) {
    params.field = field;
    $.getJSON(BASE_URL, params, function (data) {
      const options = data.options || [];
      if (options.length === 0) {
        resetSelect($target, placeholder);
      } else {
        $target.html(buildSelect(options, placeholder)).prop('disabled', false);
        // Restore saved value if it exists in the new options
        if (currentValue && options.indexOf(currentValue) !== -1) {
          $target.val(currentValue);
        }
      }
      if (typeof callback === 'function') callback();
    }).fail(function () {
      resetSelect($target, placeholder);
    });
  }

  $(document).ready(function () {
    const $state    = $('#id_assigned_state');
    const $district = $('#id_assigned_district');
    const $city     = $('#id_assigned_city');
    const $area     = $('#id_assigned_area');
    const $level    = $('#id_admin_level');

    // Saved values (on edit form — the fields already have a value from the DB)
    const savedState    = $state.val()    || '';
    const savedDistrict = $district.val() || '';
    const savedCity     = $city.val()     || '';
    const savedArea     = $area.val()     || '';

    // ── Show / hide location fields based on admin level ──────────────
    function updateVisibility() {
      const level = $level.val();
      const showState    = ['state', 'district', 'city', 'area'].includes(level);
      const showDistrict = ['district', 'city', 'area'].includes(level);
      const showCity     = ['city', 'area'].includes(level);
      const showArea     = level === 'area';

      $state.closest('.form-row').toggle(showState);
      $district.closest('.form-row').toggle(showDistrict);
      $city.closest('.form-row').toggle(showCity);
      $area.closest('.form-row').toggle(showArea);
    }

    // ── Load states from DB on page load ─────────────────────────────
    function initStates(callback) {
      $.getJSON(BASE_URL, { field: 'state' }, function (data) {
        const options = data.options || [];
        $state.html(buildSelect(options, '— Select State —')).prop('disabled', false);
        if (savedState && options.indexOf(savedState) !== -1) {
          $state.val(savedState);
        }
        if (typeof callback === 'function') callback();
      });
    }

    // ── Chain: State → District ───────────────────────────────────────
    function onStateChange(restoreDistrict) {
      const state = $state.val();
      resetSelect($district, '— Select District —');
      resetSelect($city,     '— Select City —');
      resetSelect($area,     '— Select Area / Village —');

      if (!state) return;

      loadOptions('district', { state: state }, $district, '— Select District —', restoreDistrict || '', function () {
        if (restoreDistrict) onDistrictChange(savedCity);
      });
    }

    // ── Chain: District → City ────────────────────────────────────────
    function onDistrictChange(restoreCity) {
      const state    = $state.val();
      const district = $district.val();
      resetSelect($city, '— Select City —');
      resetSelect($area, '— Select Area / Village —');

      if (!district) return;

      loadOptions('city', { state: state, district: district }, $city, '— Select City —', restoreCity || '', function () {
        if (restoreCity) onCityChange(savedArea);
      });
    }

    // ── Chain: City → Area ────────────────────────────────────────────
    function onCityChange(restoreArea) {
      const state    = $state.val();
      const district = $district.val();
      const city     = $city.val();
      resetSelect($area, '— Select Area / Village —');

      if (!city) return;

      loadOptions('area', { state: state, district: district, city: city }, $area, '— Select Area / Village —', restoreArea || '');
    }

    // ── Bind events ───────────────────────────────────────────────────
    $level.on('change', updateVisibility);
    $state.on('change', function () { onStateChange(); });
    $district.on('change', function () { onDistrictChange(); });
    $city.on('change', function () { onCityChange(); });

    // ── Initialise ────────────────────────────────────────────────────
    updateVisibility();
    initStates(function () {
      if (savedState) onStateChange(savedDistrict);
    });
  });

})(django.jQuery);
