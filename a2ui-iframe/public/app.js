/* Copyright 2026 The Project Contributors
 * Licensed under the Apache License, Version 2.0.
 */

/* Enterprise Travel Retail Pilot — Interactive Canvas State & Controller */
(function () {
  const DATA = window.A2UI_DATA || window.ENTERPRISE_DATA;

  const state = {
    activeTab: "pillar2",
    branchId: "0015",
    personaId: "jenkins",
    selectedOfferId: "offer-vista-1",
    sunFilterActive: false,
    checkedPois: {},
    checkedAncillaries: new Set(["forex", "parking"]),
    studioDialect: "northeast",
    studioFormat: "facebook",
    hasUrlStatePayload: false,
    liveTelemetryActive: false,
    liveTelemetryStamp: "",
    toastTimer: null
  };

  // Initialize default checked POIs per offer
  DATA.offers.forEach(function (offer) {
    state.checkedPois[offer.id] = new Set(
      offer.pois.filter(function (p) { return p.defaultChecked; }).map(function (p) { return p.id; })
    );
  });

  function escapeHtml(val) {
    return String(val == null ? "" : val)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function sanitizeText(val) {
    return String(val == null ? "" : val)
      .replace(/[<>"]/g, "")
      .trim();
  }

  function sanitizeHttpUrl(rawUrl, fallbackUrl) {
    const cleaned = sanitizeText(rawUrl);
    if (/^https?:\/\/[^\s"'<>]+$/i.test(cleaned)) {
      return cleaned;
    }
    return fallbackUrl || "";
  }

  function isAllowedMessageOrigin(origin) {
    if (!origin || origin === "null") return false;
    if (typeof window !== "undefined" && window.location && origin === window.location.origin) {
      return true;
    }
    return /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(origin) ||
      /^https:\/\/([a-z0-9-]+\.)*(google\.com|cloud\.google\.com|run\.app|example\.com)$/i.test(origin);
  }

  function resolveViewTab(rawView) {
    if (!rawView) return null;
    const v = String(rawView).trim().toLowerCase();
    if (v === "pillar1" || v === "pillar1_monday_planner" || v === "cockpit" || v.indexOf("pillar1") !== -1 || v.indexOf("monday") !== -1 || v.indexOf("ops") !== -1) {
      return "pillar1";
    }
    if (v === "pillar3" || v === "pillar3_marketing_studio" || v === "studio" || v.indexOf("pillar3") !== -1 || v.indexOf("marketing") !== -1) {
      return "pillar3";
    }
    if (v === "pillar2" || v === "pillar2_trip_ideation" || v === "ideator" || v === "overview" || v === "catalog_explorer" || v.indexOf("pillar2") !== -1 || v.indexOf("ideat") !== -1 || v.indexOf("catalog") !== -1) {
      return "pillar2";
    }
    return null;
  }

  function resolveBranchId(rawBranch) {
    if (!rawBranch) return null;
    const bRaw = String(rawBranch).trim();
    if (DATA.branches[bRaw]) return bRaw;
    const bNorm = bRaw.toUpperCase();
    if (bNorm === "ALL" || bNorm === "ANY" || bNorm === "*") return null;
    if (bNorm.indexOf("9024") !== -1 || bNorm.indexOf("GLA") !== -1 || bNorm.indexOf("SCOT") !== -1) {
      return "9024";
    }
    if (bNorm.indexOf("MAN") !== -1 || bNorm.indexOf("NORTH WEST") !== -1 || bNorm.indexOf("NORTHWEST") !== -1) {
      return "MAN1";
    }
    if (bNorm.indexOf("0015") !== -1 || bNorm.indexOf("NCL") !== -1 || bNorm.indexOf("NEWCASTLE") !== -1 || bNorm.indexOf("NORTH EAST") !== -1 || bNorm.indexOf("NORTHEAST") !== -1) {
      return "0015";
    }
    return null;
  }

  function resolvePersonaId(rawPersona) {
    if (!rawPersona) return null;
    const pLow = String(rawPersona).trim().toLowerCase();
    if (DATA.personas[pLow]) return pLow;
    if (pLow.indexOf("jenkins") !== -1 || pLow.indexOf("boomerang") !== -1 || pLow.indexOf("family") !== -1) {
      return "jenkins";
    }
    if (pLow.indexOf("smith") !== -1 || pLow.indexOf("prestige") !== -1 || pLow.indexOf("return") !== -1) {
      return "smith";
    }
    if (pLow.indexOf("henderson") !== -1 || pLow.indexOf("suburban") !== -1 || pLow.indexOf("short") !== -1) {
      return "henderson";
    }
    return null;
  }

  function showToast(title, detail) {
    const toastEl = document.getElementById("a2ui-toast");
    if (!toastEl) return;
    toastEl.innerHTML =
      '<div style="font-weight:800;color:var(--brand-highlight);margin-bottom:3px;">' + escapeHtml(title) + "</div>" +
      '<div style="color:#F8FAFC;font-size:0.76rem;">' + escapeHtml(detail) + "</div>";
    toastEl.classList.add("visible");
    if (state.toastTimer) clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(function () {
      toastEl.classList.remove("visible");
    }, 4200);
  }

  function getActiveBranch() {
    return DATA.branches[state.branchId] || DATA.branches["0015"];
  }

  function getActivePersona() {
    return DATA.personas[state.personaId] || DATA.personas.jenkins;
  }

  function getSelectedOffer() {
    return DATA.offers.find(function (o) { return o.id === state.selectedOfferId; }) || DATA.offers[1];
  }

  function calculateBasket() {
    const offer = getSelectedOffer();
    const persona = getActivePersona();
    const baseBasket = offer.pricePp * persona.partyMultiplier;
    let ancillaryTotal = 0;
    const selectedAncList = [];

    DATA.ancillaries.forEach(function (anc) {
      if (state.checkedAncillaries.has(anc.id)) {
        ancillaryTotal += anc.priceGbp;
        selectedAncList.push(anc.title);
      }
    });

    return {
      baseBasket: baseBasket,
      ancillaryTotal: ancillaryTotal,
      totalBasket: baseBasket + ancillaryTotal,
      selectedAncList: selectedAncList
    };
  }

  const MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function formatIsoDateLabel(rawDate) {
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(rawDate == null ? "" : rawDate).trim());
    if (!match) return "";
    const monthIdx = Number(match[2]) - 1;
    const day = Number(match[3]);
    if (monthIdx < 0 || monthIdx > 11 || day < 1 || day > 31) return "";
    return day + " " + MONTH_ABBR[monthIdx] + " " + match[1];
  }


  function parseHashState(hash) {
    if (!hash) return null;
    const stateMatch = hash.match(/state=([^&]+)/);
    if (!stateMatch || !stateMatch[1]) return null;
    const sigMatch = hash.match(/sig=([^&]+)/);
    const sig = sigMatch ? sigMatch[1] : null;
    try {
      const b64 = stateMatch[1].replace(/-/g, "+").replace(/_/g, "/");
      const padded = b64 + "===".slice((b64.length + 3) % 4);
      const rawBin = window.atob(padded);
      let jsonStr;
      if (typeof TextDecoder !== "undefined") {
        const bytes = new Uint8Array(rawBin.length);
        for (let i = 0; i < rawBin.length; i++) {
          bytes[i] = rawBin.charCodeAt(i);
        }
        jsonStr = new TextDecoder("utf-8").decode(bytes);
      } else {
        jsonStr = decodeURIComponent(escape(rawBin));
      }
      const decoded = JSON.parse(jsonStr);
      return { decoded: decoded, signature: sig };
    } catch (err) {
      console.warn("A2UI URL state hydration fallback used:", err);
      return null;
    }
  }

  function hydrateFromUrl() {
    try {
      const params = new URLSearchParams(window.location.search);
      const viewTab = resolveViewTab(params.get("view") || params.get("tab"));
      if (viewTab) {
        state.activeTab = viewTab;
      }
      const resolvedBranch = resolveBranchId(params.get("branch"));
      if (resolvedBranch) {
        state.branchId = resolvedBranch;
        state.studioDialect = getActiveBranch().defaultDialect;
      }
      const resolvedPersona = resolvePersonaId(params.get("persona"));
      if (resolvedPersona) {
        state.personaId = resolvedPersona;
      }
      const offerParam = params.get("offer");
      if (offerParam && DATA.offers.some(function (o) { return o.id === offerParam; })) {
        state.selectedOfferId = offerParam;
      }
      if (params.get("sun_filter") === "1" || params.get("sun_filter") === "true") {
        state.sunFilterActive = true;
      }

      // Base64URL #state= payload support with HMAC signature (&sig=)
      const hash = window.location.hash || "";
      const parsed = parseHashState(hash);
      if (parsed) {
        state.hasUrlStatePayload = true;
        if (parsed.signature) {
          state.urlStateSignature = parsed.signature;
        }
        applyExternalPayload(parsed.decoded);
      }
    } catch (err) {
      console.warn("A2UI URL state hydration fallback used:", err);
    }
  }

  function applyExternalPayload(rawPayload) {
    if (!rawPayload || typeof rawPayload !== "object") return;
    const params = (rawPayload.params && typeof rawPayload.params === "object") ? rawPayload.params : {};
    const dataObj = (rawPayload.data && typeof rawPayload.data === "object") ? rawPayload.data : {};
    const data = Object.assign({}, rawPayload, dataObj, params);

    const viewTab = resolveViewTab(rawPayload.view || data.view || data.view_mode);
    if (viewTab) {
      state.activeTab = viewTab;
    }

    const rawBranch =
      data.branchId ||
      data.branch_filter ||
      data.branch_or_city ||
      data.region ||
      data.branch_region ||
      rawPayload.branchId;
    const resolvedBranch = resolveBranchId(rawBranch);
    if (resolvedBranch) {
      state.branchId = resolvedBranch;
      state.studioDialect = getActiveBranch().defaultDialect;
    }

    const rawPersona = data.personaId || data.cohort_group_filter || rawPayload.personaId;
    const resolvedPersona = resolvePersonaId(rawPersona);
    if (resolvedPersona) {
      state.personaId = resolvedPersona;
    }

    if (data.selectedOfferId && DATA.offers.some(function (o) { return o.id === data.selectedOfferId; })) {
      state.selectedOfferId = data.selectedOfferId;
    }

    const incomingOffers =
      (Array.isArray(data.offers) && data.offers) ||
      (Array.isArray(data.tailored_core_offers) && data.tailored_core_offers) ||
      (Array.isArray(data.core_tailored_offers) && data.core_tailored_offers) ||
      (Array.isArray(data.top_regional_deals) && data.top_regional_deals) ||
      (Array.isArray(data.deals) && data.deals) ||
      null;

    if (incomingOffers && incomingOffers.length > 0) {
      const slotCount = Math.min(DATA.offers.length, incomingOffers.length);
      DATA.offers.length = slotCount;
      incomingOffers.slice(0, slotCount).forEach(function (incoming, idx) {
        const target = DATA.offers[idx];
        if (!target || !incoming || typeof incoming !== "object") return;

        const rawHotel =
          incoming.hotelName ||
          incoming.HotelName ||
          incoming.VoyageName ||
          incoming.ShipName ||
          incoming.hotel_name ||
          incoming.canonical_hotel_name;
        if (rawHotel) {
          target.hotelName = sanitizeText(rawHotel);
        }

        const rawResort = incoming.Resort || incoming.resort || "";
        const rawCountry = incoming.Destination || incoming.Country || incoming.DestinationSector || "";
        const rawDest =
          incoming.destination ||
          (rawResort && rawCountry && rawResort !== rawCountry
            ? rawResort + ", " + rawCountry
            : rawCountry || rawResort);
        if (rawDest) {
          target.destination = sanitizeText(rawDest);
        }

        const rawStarNum = parseInt(String(incoming.StarRating || incoming.star_rating || "").replace(/[^0-9]/g, ""), 10);
        if (!isNaN(rawStarNum) && rawStarNum >= 1 && rawStarNum <= 5) {
          target.officialRating = rawStarNum + "★ Official Tour Op";
          target.officialStars = "★★★★★".slice(0, rawStarNum);
        }

        if (incoming.IsPreferredPartner != null || incoming.IsDirectContract != null || incoming.WildcardType) {
          const isPref = Boolean(
            incoming.IsPreferredPartner ||
            incoming.IsDirectContract ||
            incoming.WildcardType === "PREFERRED_DIRECT_WILDCARD" ||
            String(incoming.SupplierID || "") === "DIR0001"
          );
          target.isPreferredPartner = isPref;
          if (incoming.SupplierID) {
            target.supplierId = sanitizeText(incoming.SupplierID);
          }
          if (incoming.WildcardType === "PREFERRED_DIRECT_WILDCARD" || isPref) {
            target.slotType = "💎 PREFERRED DIRECT CONTRACT · DIR0001";
            target.ribbonClass = "ribbon-vista";
            target.marginClass = "margin-vista";
            target.marginLabel = "18–25% Direct Tier";
          } else if (incoming.WildcardType === "CRUISE_WILDCARD") {
            target.slotType = "🚢 CRUISE WILDCARD";
            target.ribbonClass = "ribbon-core";
            target.marginClass = "margin-core";
            target.marginLabel = "Cruise Margin Tier";
          } else if (incoming.WildcardType === "LONG_HAUL_WILDCARD") {
            target.slotType = "🌴 LONG-HAUL WILDCARD";
            target.ribbonClass = "ribbon-core";
            target.marginClass = "margin-core";
            target.marginLabel = "Long-Haul Tier";
          } else {
            target.slotType = "CORE MOSAIC MATCH";
            target.ribbonClass = "ribbon-core";
            target.marginClass = "margin-core";
            target.marginLabel = sanitizeText(incoming.SupplierName || "Approved Tour Op");
          }
        }

        const rawBoard = incoming.boardBasis || incoming.BoardBasis || incoming.board_basis;
        if (rawBoard) {
          target.boardBasis = sanitizeText(rawBoard);
        }

        const rawNights = Number(
          incoming.nights ||
          incoming.TypicalDurationNights ||
          incoming.Duration ||
          incoming.duration_nights
        );
        if (rawNights > 0) {
          target.nights = rawNights;
        }

        const avgGross = Number(incoming.AvgGrossPriceGBP || incoming.GrossPrice || 0);
        const rawPricePp = Number(
          incoming.pricePp ||
          incoming.PricePerPersonGBP ||
          incoming.AvgPricePerPersonGBP ||
          incoming.price_per_person_gbp ||
          (avgGross > 0 ? Math.round(avgGross / 2) : 0)
        );
        if (rawPricePp > 0) {
          target.pricePp = Math.round(rawPricePp);
        }

        const wn = incoming.weathernext_outlook || incoming.weathernext || {};
        const destWn = wn.destination_weathernext || {};
        if (
          wn.data_source === "GOOGLE_WEATHERNEXT_API_LIVE" ||
          wn.data_source === "BIGQUERY_WEATHERNEXT_LIVE" ||
          destWn.data_source === "GOOGLE_WEATHERNEXT_API_LIVE" ||
          destWn.data_source === "BIGQUERY_WEATHERNEXT_LIVE"
        ) {
          state.liveTelemetryActive = true;
          if (wn.forecast_generated_at_utc) {
            state.liveTelemetryStamp = String(wn.forecast_generated_at_utc).slice(11, 16) + " UTC";
          } else if (!state.liveTelemetryStamp) {
            state.liveTelemetryStamp = new Date().toISOString().slice(11, 16) + " UTC";
          }
        }

        const inLat = Number(
          incoming.lat ||
          incoming.latitude ||
          destWn.lat ||
          (incoming.poi_trip_ideation &&
            incoming.poi_trip_ideation.points_of_interest &&
            incoming.poi_trip_ideation.points_of_interest[0] &&
            incoming.poi_trip_ideation.points_of_interest[0].lat)
        );
        const inLon = Number(
          incoming.lon ||
          incoming.lng ||
          incoming.longitude ||
          destWn.lon ||
          (incoming.poi_trip_ideation &&
            incoming.poi_trip_ideation.points_of_interest &&
            incoming.poi_trip_ideation.points_of_interest[0] &&
            incoming.poi_trip_ideation.points_of_interest[0].lon)
        );
        if (!isNaN(inLat) && !isNaN(inLon) && inLat !== 0 && inLon !== 0) {
          target.lat = inLat;
          target.lon = inLon;
        }

        const rawSunScore =
          incoming.sunScore != null
            ? incoming.sunScore
            : (wn.sun_seeker_score != null ? wn.sun_seeker_score : wn.sun_index_score);
        if (rawSunScore != null && !isNaN(Number(rawSunScore))) {
          target.sunScore = Math.round(Number(rawSunScore));
        }

        const rawTempC =
          incoming.destTempC != null
            ? incoming.destTempC
            : (destWn.avg_high_c != null ? destWn.avg_high_c : wn.avg_daytime_high_c);
        if (rawTempC != null && !isNaN(Number(rawTempC))) {
          target.destTempC = Math.round(Number(rawTempC));
        }

        const rawSunProb =
          incoming.sunProbPct != null ? incoming.sunProbPct : destWn.sunshine_prob_pct;
        if (rawSunProb != null && !isNaN(Number(rawSunProb))) {
          target.sunProbPct = Math.round(Number(rawSunProb));
        }

        const rawRainRisk = Number(incoming.rainRiskPct != null ? incoming.rainRiskPct : destWn.rain_risk_pct);
        if (!isNaN(rawRainRisk) && rawRainRisk >= 0 && (incoming.rainRiskPct != null || destWn.rain_risk_pct != null)) {
          target.rainRiskPct = Math.round(rawRainRisk);
        }

        const rawUv =
          incoming.uvIndex != null
            ? incoming.uvIndex
            : (destWn.uv_index != null ? destWn.uv_index : destWn.uv_index_max);
        if (rawUv != null && !isNaN(Number(rawUv))) {
          target.uvIndex = Math.round(Number(rawUv));
        }

        const rawDeltaVal =
          incoming.tempDeltaC != null
            ? incoming.tempDeltaC
            : (wn.thermal_uplift_c != null
              ? wn.thermal_uplift_c
              : (wn.temp_delta_vs_uk_c != null ? wn.temp_delta_vs_uk_c : wn.temperature_uplift_c));
        const rawDelta = Number(rawDeltaVal);
        if (!isNaN(rawDelta) && rawDeltaVal != null) {
          target.tempDeltaC = Math.round(rawDelta);
        }

        const rawEnsemble =
          incoming.ensemble7Day ||
          wn.daily_forecast ||
          destWn.daily_7day_strip ||
          wn.daily_7day_forecast;
        if (Array.isArray(rawEnsemble) && rawEnsemble.length > 0) {
          target.ensemble7Day = rawEnsemble.slice(0, 7).map(function (d, dIdx) {
            const fallbackDay = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dIdx % 7];
            const dayName =
              d.day ||
              d.day_label ||
              (d.date ? new Date(d.date + "T12:00:00Z").toLocaleDateString("en-GB", { weekday: "short", timeZone: "UTC" }) : fallbackDay);
            const highC = Math.round(
              Number(
                d.temp != null
                  ? d.temp
                  : (d.temp_high_c != null ? d.temp_high_c : (d.high_c != null ? d.high_c : target.destTempC))
              )
            );
            const rawProbVal = d.prob != null ? d.prob : (d.sun_prob_pct != null ? d.sun_prob_pct : d.sunshine_prob_pct);
            const sunPct = rawProbVal != null ? String(rawProbVal) : (target.sunProbPct + "%");
            const iconVal = sanitizeText(d.icon || (Number(d.rain_prob_pct || 0) > 45 ? "🌦️" : (highC >= 22 ? "☀️" : "🌤️")));
            return {
              day: sanitizeText(dayName),
              icon: iconVal,
              temp: highC,
              prob: sanitizeText(sunPct.indexOf("%") === -1 ? sunPct + "%" : sunPct)
            };
          });
        }

        const rawHook = incoming.weatherHook || wn.pitch_hook;
        if (rawHook) {
          target.weatherHook = sanitizeText(rawHook);
        }
      });
    }
  }

  // Listen for runtime postMessage payloads
  window.addEventListener("message", function (event) {
    if (!isAllowedMessageOrigin(event.origin)) return;
    if (!event.data || typeof event.data !== "object") return;
    if (event.data.type === "a2ui_hydrate" || event.data.type === "state_update") {
      applyExternalPayload(event.data.payload || event.data.data || event.data);
      renderAll();
    }
  });

  function renderCommandBar() {
    const branchSel = document.getElementById("branch-selector");
    const personaSel = document.getElementById("persona-selector");
    if (branchSel) branchSel.value = state.branchId;
    if (personaSel) personaSel.value = state.personaId;

    const liveBadge = document.getElementById("live-telemetry-badge");
    if (liveBadge) {
      liveBadge.textContent = state.liveTelemetryActive
        ? "🟢 LIVE FORECAST • " + state.liveTelemetryStamp
        : "🟢 LIVE SYNC • Weather & Places";
    }

    document.querySelectorAll(".mode-tab").forEach(function (btn) {
      const tabId = btn.getAttribute("data-tab");
      btn.classList.toggle("active", tabId === state.activeTab);
      btn.setAttribute("aria-selected", tabId === state.activeTab ? "true" : "false");
    });

    document.querySelectorAll(".tab-panel").forEach(function (panel) {
      const isActive = panel.id === "panel-" + state.activeTab;
      panel.classList.toggle("active", isActive);
      if (isActive) {
        panel.removeAttribute("hidden");
      } else {
        panel.setAttribute("hidden", "hidden");
      }
    });
  }

  function renderWeatherNextBanner() {
    const branch = getActiveBranch();
    const offer = getSelectedOffer();
    const tempDiff = offer.destTempC - branch.ukTempC;
    offer.tempDeltaC = tempDiff;
    const diffSign = tempDiff >= 0 ? "+" + tempDiff : String(tempDiff);

    const ukBox = document.getElementById("wn-local-box");
    if (ukBox) {
      ukBox.innerHTML =
        '<div style="font-size:2rem;">' + branch.ukIcon + "</div>" +
        "<div>" +
          '<div style="font-size:0.68rem;text-transform:uppercase;color:#94A3B8;font-weight:700;">DEPARTING FROM ' + escapeHtml(branch.airportName) + "</div>" +
          '<div style="font-size:0.95rem;font-weight:700;">' + branch.ukTempC + "°C · " + branch.ukRainProb + "% Rain · " + escapeHtml(branch.ukCondition) + "</div>" +
        "</div>";
    }

    const bridgeBox = document.getElementById("wn-bridge");
    if (bridgeBox) {
      const rainRisk = offer.rainRiskPct != null ? offer.rainRiskPct : 8;
      const uvIdx = offer.uvIndex != null ? offer.uvIndex : 7;
      bridgeBox.innerHTML =
        '<div style="background:rgba(2,132,199,0.2);color:#38BDF8;font-size:0.75rem;font-weight:800;padding:4px 10px;border-radius:9999px;display:inline-block;margin-bottom:4px;">🔥 ' + diffSign + "°C THERMAL UPLIFT</div>" +
        '<div style="font-size:0.75rem;color:#E2E8F0;">☀️ Climate Score: ' + offer.sunScore + "/100 (" + offer.sunProbPct + "% Sun · " + rainRisk + "% Rain · UV " + uvIdx + ")</div>";
    }

    const ensembleWrap = document.getElementById("wn-ensemble-wrap");
    if (ensembleWrap && Array.isArray(offer.ensemble7Day)) {
      ensembleWrap.innerHTML =
        '<div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:4px;">' +
        offer.ensemble7Day.map(function (d) {
          return (
            '<div style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:6px;padding:6px 10px;text-align:center;font-size:0.72rem;min-width:44px;">' +
              '<div style="color:#94A3B8;font-weight:700;">' + escapeHtml(d.day) + "</div>" +
              '<div style="font-size:1.1rem;margin:2px 0;">' + d.icon + "</div>" +
              '<div style="font-weight:800;color:#F8FAFC;">' + d.temp + "°</div>" +
            "</div>"
          );
        }).join("") +
        "</div>";
    }

    const filterBtn = document.getElementById("btn-weather-filter");
    if (filterBtn) {
      filterBtn.textContent = state.sunFilterActive ? "✓ High-Sun Filter Active (>90%)" : "Filter by Optimal Climate";
      filterBtn.style.backgroundColor = state.sunFilterActive ? "var(--status-success)" : "var(--brand-accent)";
    }
  }

  function renderPillar2Offers() {
    const grid = document.getElementById("offers-comparator-grid");
    if (!grid) return;

    let displayOffers = DATA.offers;
    if (state.sunFilterActive) {
      displayOffers = DATA.offers.filter(function (o) { return o.sunScore >= 90; });
    }

    grid.innerHTML = displayOffers.map(function (offer) {
      const isSelected = offer.id === state.selectedOfferId;
      return (
        '<article class="offer-card' + (isSelected ? ' selected' : '') + '" style="' + (isSelected ? 'border-color:var(--brand-accent);box-shadow:0 0 0 2px var(--brand-accent);' : '') + '" data-offer-id="' + escapeHtml(offer.id) + '">' +
          '<div class="offer-card-header" style="background:' + escapeHtml(offer.headerGradient || 'var(--brand-primary)') + ';color:#FFFFFF;">' +
            '<div style="font-size:0.75rem;font-weight:800;letter-spacing:0.04em;">' + escapeHtml(offer.slotType) + '</div>' +
            '<div style="font-size:0.72rem;background:rgba(255,255,255,0.2);padding:2px 6px;border-radius:4px;font-weight:700;">' + escapeHtml(offer.marginLabel) + '</div>' +
          '</div>' +
          '<div class="offer-card-body">' +
            '<div style="font-size:1.05rem;font-weight:700;color:var(--text-primary);margin-bottom:4px;">' + escapeHtml(offer.hotelName) + '</div>' +
            '<div style="font-size:0.78rem;color:var(--text-muted);margin-bottom:10px;">📍 ' + escapeHtml(offer.destination) + ' · ' + escapeHtml(offer.officialRating) + '</div>' +
            '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px;">' +
              '<div>' +
                '<span class="offer-price">£' + offer.pricePp + '</span>' +
                '<span style="font-size:0.75rem;color:var(--text-muted);"> pp</span>' +
              '</div>' +
              '<div style="font-size:0.75rem;font-weight:700;color:var(--brand-accent);">⭐ ' + offer.googleRating + ' (' + escapeHtml(offer.googleReviews) + ' reviews)</div>' +
            '</div>' +
            '<p style="font-size:0.78rem;color:var(--text-secondary);line-height:1.4;margin-bottom:12px;">' + escapeHtml(offer.weatherHook) + '</p>' +
            '<button type="button" class="btn-select-offer" style="width:100%;padding:8px;border-radius:6px;border:none;background:' + (isSelected ? 'var(--status-success)' : 'var(--brand-primary)') + ';color:#FFFFFF;font-weight:700;font-size:0.8rem;cursor:pointer;">' +
              (isSelected ? '✓ Active Selection' : 'Select Package') +
            '</button>' +
          '</div>' +
        '</article>'
      );
    }).join("");

    grid.querySelectorAll(".offer-card").forEach(function (card) {
      card.addEventListener("click", function () {
        const offId = card.getAttribute("data-offer-id");
        if (offId) {
          state.selectedOfferId = offId;
          if (window.emit) {
            window.emit("select_offer_card", { offerId: offId, branchId: state.branchId, personaId: state.personaId });
          }
          renderAll();
        }
      });
    });
  }

  function renderPillar2Drawer() {
    const offer = getSelectedOffer();
    const persona = getActivePersona();

    const nameEl = document.getElementById("poi-selected-item-name");
    if (nameEl) nameEl.textContent = offer.destination;

    const poiGrid = document.getElementById("poi-cards-grid");
    if (poiGrid && Array.isArray(offer.pois)) {
      const checkedSet = state.checkedPois[offer.id] || new Set();
      poiGrid.innerHTML = offer.pois.map(function (p) {
        const isChecked = checkedSet.has(p.id);
        return (
          '<div class="poi-card' + (isChecked ? ' selected' : '') + '" data-poi-id="' + escapeHtml(p.id) + '">' +
            '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">' +
              '<span style="font-weight:700;font-size:0.72rem;color:var(--brand-accent);">' + escapeHtml(p.category) + '</span>' +
              '<span style="font-size:0.72rem;color:var(--text-muted);">' + escapeHtml(p.rating) + '</span>' +
            '</div>' +
            '<div style="font-weight:700;color:var(--text-primary);margin-bottom:2px;">' + escapeHtml(p.name) + '</div>' +
            '<div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:4px;">' + escapeHtml(p.distance) + ' · ' + escapeHtml(p.daySlot) + '</div>' +
            '<div style="font-size:0.72rem;color:var(--text-secondary);">' + escapeHtml(p.hook) + '</div>' +
          '</div>'
        );
      }).join("");

      poiGrid.querySelectorAll(".poi-card").forEach(function (pCard) {
        pCard.addEventListener("click", function () {
          const pid = pCard.getAttribute("data-poi-id");
          if (!state.checkedPois[offer.id]) state.checkedPois[offer.id] = new Set();
          const pSet = state.checkedPois[offer.id];
          if (pSet.has(pid)) {
            pSet.delete(pid);
          } else {
            pSet.add(pid);
          }
          if (window.emit) {
            window.emit("toggle_poi_itinerary", { offerId: offer.id, poiId: pid, checked: pSet.has(pid) });
          }
          renderPillar2Drawer();
          renderStickyBar();
        });
      });
    }

    const itinList = document.getElementById("itinerary-days-list");
    const countPill = document.getElementById("itinerary-count-pill");
    if (itinList) {
      const checkedSet = state.checkedPois[offer.id] || new Set();
      const selectedPois = (offer.pois || []).filter(function (p) { return checkedSet.has(p.id); });
      if (countPill) countPill.textContent = selectedPois.length + " Selected";

      if (selectedPois.length === 0) {
        itinList.innerHTML = '<div style="font-size:0.75rem;color:var(--text-muted);padding:8px 0;">No activities selected. Click points of interest above to populate this itinerary.</div>';
      } else {
        itinList.innerHTML = selectedPois.map(function (p) {
          return (
            '<div style="padding:6px 0;border-bottom:1px solid rgba(0,0,0,0.06);font-size:0.75rem;">' +
              '<strong>' + escapeHtml(p.daySlot) + ':</strong> ' + escapeHtml(p.name) + ' (' + escapeHtml(p.hook) + ')' +
            '</div>'
          );
        }).join("");
      }
    }

    const ancList = document.getElementById("ancillary-checkbox-list");
    if (ancList) {
      ancList.innerHTML = DATA.ancillaries.map(function (anc) {
        const isChecked = state.checkedAncillaries.has(anc.id);
        return (
          '<label class="ancillary-item" style="cursor:pointer;' + (isChecked ? 'background:#F0FDF4;border-color:var(--status-success);' : '') + '">' +
            '<div style="display:flex;align-items:center;gap:8px;">' +
              '<input type="checkbox" data-anc-id="' + escapeHtml(anc.id) + '" ' + (isChecked ? 'checked' : '') + ' style="accent-color:var(--brand-accent);" />' +
              '<div>' +
                '<div style="font-weight:700;color:var(--text-primary);">' + anc.icon + ' ' + escapeHtml(anc.title) + '</div>' +
                '<div style="font-size:0.7rem;color:var(--text-muted);">' + escapeHtml(anc.gapStatus) + '</div>' +
              '</div>' +
            '</div>' +
            '<div style="font-weight:800;color:var(--brand-primary);font-size:0.8rem;">' + escapeHtml(anc.priceLabel) + '</div>' +
          '</label>'
        );
      }).join("");

      ancList.querySelectorAll("input[type='checkbox']").forEach(function (cb) {
        cb.addEventListener("change", function () {
          const aid = cb.getAttribute("data-anc-id");
          if (cb.checked) {
            state.checkedAncillaries.add(aid);
          } else {
            state.checkedAncillaries.delete(aid);
          }
          if (window.emit) {
            window.emit("toggle_ancillary_gap", { ancillaryId: aid, checked: cb.checked });
          }
          renderPillar2Drawer();
          renderStickyBar();
        });
      });
    }

    const basketSummary = document.getElementById("live-basket-summary");
    if (basketSummary) {
      const basket = calculateBasket();
      basketSummary.innerHTML =
        '<div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:0.78rem;">' +
          '<span>Base Package (' + persona.partySummary + '):</span>' +
          '<strong>£' + basket.baseBasket.toLocaleString() + '</strong>' +
        '</div>' +
        '<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:0.78rem;color:var(--text-secondary);">' +
          '<span>Attached Ancillaries (' + state.checkedAncillaries.size + '):</span>' +
          '<strong>+£' + basket.ancillaryTotal.toLocaleString() + '</strong>' +
        '</div>' +
        '<div style="display:flex;justify-content:space-between;padding-top:8px;border-top:1px solid #BFDBFE;font-size:0.95rem;font-weight:800;color:var(--brand-primary);">' +
          '<span>Total Basket Value:</span>' +
          '<span>£' + basket.totalBasket.toLocaleString() + '</span>' +
        '</div>';
    }
  }

  function renderPillar3Studio() {
    const offer = getSelectedOffer();
    const branch = getActiveBranch();
    const persona = getActivePersona();
    const dialect = DATA.dialects[state.studioDialect] || DATA.dialects.northeast;

    const offerSelect = document.getElementById("studio-offer-select");
    if (offerSelect) {
      offerSelect.value = state.selectedOfferId;
    }

    const preview = document.getElementById("studio-preview-canvas");
    if (preview) {
      const p1 = offer.pois && offer.pois[0] ? offer.pois[0].name : "Beachfront Promenade";
      const p2 = offer.pois && offer.pois[1] ? offer.pois[1].name : "Local Dining Gem";

      const headline = dialect.headlinePrefix
        .replace("{ukTemp}", String(branch.ukTempC))
        .replace("{city}", branch.shortName)
        .replace("{destTemp}", String(offer.destTempC))
        .replace("{dest}", offer.destination);

      const body = dialect.bodyTemplate
        .replace(/{ukTemp}/g, String(branch.ukTempC))
        .replace(/{ukCond}/g, branch.ukCondition)
        .replace(/{ukRain}/g, String(branch.ukRainProb))
        .replace(/{city}/g, branch.shortName)
        .replace(/{destTemp}/g, String(offer.destTempC))
        .replace(/{dest}/g, offer.destination)
        .replace(/{tempDiff}/g, String(offer.tempDeltaC))
        .replace(/{airport}/g, branch.airportName)
        .replace(/{hotel}/g, offer.hotelName)
        .replace(/{officialRating}/g, offer.officialRating)
        .replace(/{nights}/g, String(offer.nights))
        .replace(/{board}/g, offer.boardBasis)
        .replace(/{pricePp}/g, String(offer.pricePp))
        .replace(/{googleRating}/g, String(offer.googleRating))
        .replace(/{googleReviews}/g, offer.googleReviews)
        .replace(/{poi1}/g, p1)
        .replace(/{poi2}/g, p2)
        .replace(/{branchName}/g, branch.shortName);

      preview.innerHTML =
        '<div style="font-size:0.75rem;font-weight:800;color:var(--brand-accent);text-transform:uppercase;margin-bottom:8px;">' +
          escapeHtml(state.studioFormat.toUpperCase()) + ' ASSET PREVIEW · ' + escapeHtml(branch.shortName) +
        '</div>' +
        '<div style="background:#0F172A;color:#FFFFFF;padding:12px;border-radius:8px;font-size:0.85rem;font-weight:700;margin-bottom:12px;line-height:1.4;">' +
          escapeHtml(headline) +
        '</div>' +
        '<div style="background:var(--surface-canvas);border:1px solid var(--border-subtle);padding:14px;border-radius:8px;font-size:0.8rem;white-space:pre-wrap;line-height:1.5;color:var(--text-secondary);">' +
          escapeHtml(body) + '\n\n' + escapeHtml(dialect.hashtags) +
        '</div>';
    }

    const cohortBox = document.getElementById("studio-mosaic-target");
    if (cohortBox) {
      cohortBox.innerHTML =
        '<strong>Active Customer Target:</strong> ' + escapeHtml(persona.label) + '<br/>' +
        '<span style="color:var(--text-muted);font-size:0.72rem;">Audience Distribution: ' + escapeHtml(persona.audienceSplit) + '</span>';
    }
  }

  function renderPillar1Cockpit() {
    const branch = getActiveBranch();

    const kpiRow = document.getElementById("cockpit-kpi-row");
    if (kpiRow && branch.kpi) {
      kpiRow.innerHTML =
        '<div class="kpi-card">' +
          '<div class="kpi-val">' + branch.kpi.yesterdayBookings + '</div>' +
          '<div class="kpi-lbl">Yesterday Bookings</div>' +
        '</div>' +
        '<div class="kpi-card">' +
          '<div class="kpi-val">£' + branch.kpi.yesterdayGross.toLocaleString() + '</div>' +
          '<div class="kpi-lbl">Yesterday Gross Margin Volume</div>' +
        '</div>' +
        '<div class="kpi-card">' +
          '<div class="kpi-val">' + branch.kpi.mtdBookings + '</div>' +
          '<div class="kpi-lbl">MTD Bookings (Oct 2026)</div>' +
        '</div>' +
        '<div class="kpi-card">' +
          '<div class="kpi-val">' + branch.kpi.preferredSharePct + '%</div>' +
          '<div class="kpi-lbl">Direct Partner Share (Target 20%)</div>' +
        '</div>';
    }

    const t7Queue = document.getElementById("t7-welcome-queue");
    if (t7Queue && Array.isArray(DATA.welcomeHomeQueue)) {
      t7Queue.innerHTML = DATA.welcomeHomeQueue.map(function (item) {
        return (
          '<div class="queue-item">' +
            '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">' +
              '<strong>' + escapeHtml(item.customerName) + ' (' + escapeHtml(item.bookingRef) + ')</strong>' +
              '<span class="badge-subtle">Returned ' + item.returnedDaysAgo + 'd ago</span>' +
            '</div>' +
            '<div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:4px;">Trip: ' + escapeHtml(item.returnedFrom) + ' · Spend: £' + item.priorSpendGbp.toLocaleString() + '</div>' +
            '<div style="font-size:0.74rem;color:var(--text-secondary);margin-bottom:8px;">💡 ' + escapeHtml(item.upsellHook) + '</div>' +
            '<button type="button" class="btn-log-t7" data-ref="' + escapeHtml(item.bookingRef) + '" style="font-size:0.72rem;padding:4px 8px;border-radius:4px;border:1px solid var(--border-subtle);background:#FFFFFF;cursor:pointer;">' +
              (item.callLogged ? '✓ Call Logged' : '📞 Log Follow-Up Interaction') +
            '</button>' +
          '</div>'
        );
      }).join("");

      t7Queue.querySelectorAll(".btn-log-t7").forEach(function (btn) {
        btn.addEventListener("click", function () {
          const ref = btn.getAttribute("data-ref");
          const qItem = DATA.welcomeHomeQueue.find(function (i) { return i.bookingRef === ref; });
          if (qItem) {
            qItem.callLogged = true;
            if (window.emit) {
              window.emit("log_t7_welcome_call", { bookingRef: ref, customerName: qItem.customerName });
            }
            showToast("Interaction Logged", "Follow-up interaction recorded for " + qItem.customerName);
            renderPillar1Cockpit();
          }
        });
      });
    }

    const balQueue = document.getElementById("balance-due-queue");
    if (balQueue && Array.isArray(DATA.balanceDueQueue)) {
      balQueue.innerHTML = DATA.balanceDueQueue.map(function (item) {
        return (
          '<div class="queue-item">' +
            '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">' +
              '<strong>' + escapeHtml(item.customerName) + ' (' + escapeHtml(item.bookingRef) + ')</strong>' +
              '<span style="font-weight:700;color:var(--status-danger);font-size:0.72rem;">Due in ' + item.dueInDays + ' days</span>' +
            '</div>' +
            '<div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:4px;">Departs: ' + escapeHtml(item.departsDate) + ' · ' + escapeHtml(item.destination) + '</div>' +
            '<div style="display:flex;justify-content:space-between;align-items:center;">' +
              '<div style="font-weight:800;color:var(--brand-primary);font-size:0.78rem;">Outstanding: £' + item.outstandingGbp.toFixed(2) + '</div>' +
              '<button type="button" class="btn-remind" data-ref="' + escapeHtml(item.bookingRef) + '" style="font-size:0.72rem;padding:4px 8px;border-radius:4px;border:1px solid var(--border-subtle);background:#FFFFFF;cursor:pointer;">' +
                (item.reminded ? '✓ Reminded' : '✉️ Send Balance Notice') +
              '</button>' +
            '</div>' +
          '</div>'
        );
      }).join("");

      balQueue.querySelectorAll(".btn-remind").forEach(function (btn) {
        btn.addEventListener("click", function () {
          const ref = btn.getAttribute("data-ref");
          const qItem = DATA.balanceDueQueue.find(function (i) { return i.bookingRef === ref; });
          if (qItem) {
            qItem.reminded = true;
            if (window.emit) {
              window.emit("send_balance_reminder", { bookingRef: ref, customerName: qItem.customerName, outstandingGbp: qItem.outstandingGbp });
            }
            showToast("Balance Notice Sent", "Notification dispatched for " + qItem.customerName);
            renderPillar1Cockpit();
          }
        });
      });
    }
  }

  function renderStickyBar() {
    const strip = document.getElementById("sticky-summary-strip");
    if (!strip) return;

    const offer = getSelectedOffer();
    const basket = calculateBasket();
    const checkedPois = state.checkedPois[offer.id] || new Set();

    strip.innerHTML =
      '<div style="font-size:0.85rem;font-weight:800;color:var(--brand-primary);">' +
        escapeHtml(offer.hotelName) + ' (' + escapeHtml(offer.destination) + ')' +
      '</div>' +
      '<div style="font-size:0.75rem;color:var(--text-secondary);">' +
        'Package: £' + offer.pricePp + 'pp · Total: £' + basket.totalBasket.toLocaleString() + ' (' + checkedPois.size + ' Activities, ' + state.checkedAncillaries.size + ' Ancillaries attached)' +
      '</div>';
  }

  function renderAll() {
    renderCommandBar();
    renderWeatherNextBanner();
    renderPillar2Offers();
    renderPillar2Drawer();
    renderPillar3Studio();
    renderPillar1Cockpit();
    renderStickyBar();
  }

  function setupEventHandlers() {
    const branchSel = document.getElementById("branch-selector");
    if (branchSel) {
      branchSel.addEventListener("change", function () {
        state.branchId = branchSel.value;
        state.studioDialect = getActiveBranch().defaultDialect;
        if (window.emit) {
          window.emit("switch_branch_context", { branchId: state.branchId });
        }
        renderAll();
      });
    }

    const personaSel = document.getElementById("persona-selector");
    if (personaSel) {
      personaSel.addEventListener("change", function () {
        state.personaId = personaSel.value;
        if (window.emit) {
          window.emit("switch_customer_persona", { personaId: state.personaId });
        }
        renderAll();
      });
    }

    document.querySelectorAll(".mode-tab").forEach(function (tabBtn) {
      tabBtn.addEventListener("click", function () {
        const tab = tabBtn.getAttribute("data-tab");
        if (tab) {
          state.activeTab = tab;
          if (window.emit) {
            window.emit("switch_workspace_tab", { tab: tab });
          }
          renderCommandBar();
        }
      });
    });

    const sunFilterBtn = document.getElementById("btn-weather-filter");
    if (sunFilterBtn) {
      sunFilterBtn.addEventListener("click", function () {
        state.sunFilterActive = !state.sunFilterActive;
        if (window.emit) {
          window.emit("filter_weathernext_sun_window", { active: state.sunFilterActive });
        }
        renderWeatherNextBanner();
        renderPillar2Offers();
      });
    }

    const studioOfferSel = document.getElementById("studio-offer-select");
    if (studioOfferSel) {
      studioOfferSel.addEventListener("change", function () {
        state.selectedOfferId = studioOfferSel.value;
        renderAll();
      });
    }

    document.querySelectorAll("[data-dialect]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll("[data-dialect]").forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        state.studioDialect = btn.getAttribute("data-dialect");
        if (window.emit) {
          window.emit("switch_marketing_dialect", { dialect: state.studioDialect });
        }
        renderPillar3Studio();
      });
    });

    document.querySelectorAll("[data-format]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll("[data-format]").forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        state.studioFormat = btn.getAttribute("data-format");
        if (window.emit) {
          window.emit("switch_marketing_format", { format: state.studioFormat });
        }
        renderPillar3Studio();
      });
    });

    const copyBtn = document.getElementById("btn-copy-compliant-post");
    if (copyBtn) {
      copyBtn.addEventListener("click", function () {
        const preview = document.getElementById("studio-preview-canvas");
        if (preview && navigator.clipboard) {
          navigator.clipboard.writeText(preview.innerText || "");
          showToast("Copy Dispatched", "Asset caption and disclaimers copied to clipboard.");
          if (window.emit) {
            window.emit("copy_marketing_caption", { offerId: state.selectedOfferId, dialect: state.studioDialect });
          }
        }
      });
    }

    const publishBtn = document.getElementById("btn-publish-amplify");
    if (publishBtn) {
      publishBtn.addEventListener("click", function () {
        showToast("Publish Dispatched", "Campaign published to enterprise channels via agent action.");
        if (window.emit) {
          window.emit("publish_marketing_asset", { offerId: state.selectedOfferId, dialect: state.studioDialect, format: state.studioFormat });
        }
      });
    }

    const jumpStudioBtn = document.getElementById("btn-open-marketing-studio");
    if (jumpStudioBtn) {
      jumpStudioBtn.addEventListener("click", function () {
        state.activeTab = "pillar3";
        if (window.emit) {
          window.emit("open_marketing_studio", { offerId: state.selectedOfferId });
        }
        renderCommandBar();
        renderPillar3Studio();
      });
    }

    const sendPitchBtn = document.getElementById("btn-send-pitch");
    if (sendPitchBtn) {
      sendPitchBtn.addEventListener("click", function () {
        const offer = getSelectedOffer();
        const basket = calculateBasket();
        const checkedPois = state.checkedPois[offer.id] || new Set();
        const selectedPoiObjs = (offer.pois || []).filter(function (p) { return checkedPois.has(p.id); });

        const payload = {
          offerId: offer.id,
          hotelName: offer.hotelName,
          destination: offer.destination,
          pricePp: offer.pricePp,
          totalBasket: basket.totalBasket,
          selectedAncillaries: basket.selectedAncList,
          selectedPointsOfInterest: selectedPoiObjs.map(function (p) { return p.name; }),
          branchId: state.branchId,
          personaId: state.personaId
        };

        if (window.emit) {
          window.emit("send_curated_pitch", payload);
        }
        showToast("Package Dispatched", "Curated pitch sent to enterprise assistant stream.");
      });
    }
  }

  // Initialize
  hydrateFromUrl();
  setupEventHandlers();
  renderAll();
})();
