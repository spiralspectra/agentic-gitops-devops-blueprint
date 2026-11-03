/* Copyright 2026 The Project Contributors
 * Licensed under the Apache License, Version 2.0.
 */

/* Enterprise Travel Retail Pilot — Pre-Loaded Dataset & Live Coordinates */
window.A2UI_DATA = {
  branches: {
    "0015": {
      id: "0015",
      label: "Newcastle Central (NCL) — North East Hub",
      shortName: "Newcastle Central",
      region: "North East",
      airportIata: "NCL",
      airportName: "Newcastle (NCL)",
      lat: 55.0375,
      lon: -1.6917,
      ukTempC: 9,
      ukRainProb: 82,
      ukCondition: "Overcast & Gusty Rain",
      ukIcon: "🌧️",
      defaultDialect: "northeast",
      hasForex: true,
      kpi: {
        yesterdayBookings: 14,
        yesterdayPax: 38,
        yesterdayGross: 34820,
        yesterdayProfit: 4180,
        mtdStartDate: "2026-10-01",
        mtdBookings: 112,
        mtdPax: 304,
        mtdGross: 268400,
        mtdProfit: 32210,
        preferredSharePct: 24
      }
    },
    "9024": {
      id: "9024",
      label: "Glasgow Buchanan St (GLA) — Scotland Hub",
      shortName: "Glasgow Buchanan St",
      region: "Scotland",
      airportIata: "GLA",
      airportName: "Glasgow (GLA)",
      lat: 55.8719,
      lon: -4.4331,
      ukTempC: 7,
      ukRainProb: 88,
      ukCondition: "Heavy Dreich Rain",
      ukIcon: "🌧️",
      defaultDialect: "scotland",
      hasForex: true,
      kpi: {
        yesterdayBookings: 16,
        yesterdayPax: 44,
        yesterdayGross: 39450,
        yesterdayProfit: 4720,
        mtdStartDate: "2026-10-01",
        mtdBookings: 124,
        mtdPax: 336,
        mtdGross: 294100,
        mtdProfit: 35290,
        preferredSharePct: 27
      }
    },
    "MAN1": {
      id: "MAN1",
      label: "Manchester Central (MAN) — North West Hub",
      shortName: "Manchester Central",
      region: "North West",
      airportIata: "MAN",
      airportName: "Manchester (MAN)",
      lat: 53.3537,
      lon: -2.2750,
      ukTempC: 10,
      ukRainProb: 76,
      ukCondition: "Blustery Showers",
      ukIcon: "🌦️",
      defaultDialect: "northwest",
      hasForex: true,
      kpi: {
        yesterdayBookings: 19,
        yesterdayPax: 51,
        yesterdayGross: 46200,
        yesterdayProfit: 5490,
        mtdStartDate: "2026-10-01",
        mtdBookings: 138,
        mtdPax: 372,
        mtdGross: 332800,
        mtdProfit: 39940,
        preferredSharePct: 22
      }
    }
  },

  personas: {
    jenkins: {
      id: "jenkins",
      name: "Mrs Sarah Jenkins",
      label: "Mrs Sarah Jenkins (Family Sun · Mosaic: Boomerang Boarders)",
      mosaicCohort: "Boomerang Boarders (Family Sun)",
      confidenceScore: 482,
      partySummary: "2 Adults, 1 Child (total party 3)",
      partyMultiplier: 3,
      defaultOfferId: "offer-vista-1",
      defaultAncillaries: ["forex", "parking"],
      audienceSplit: "64% Multi-Gen / Family · 36% Couples"
    },
    smith: {
      id: "smith",
      name: "Mr & Mrs Smith",
      label: "Mr & Mrs Smith (T+7 Tenerife Returner · Mosaic: Prestige Positions)",
      mosaicCohort: "Prestige Positions / Premier Couples",
      confidenceScore: 495,
      partySummary: "2 Adults sharing (couple)",
      partyMultiplier: 2,
      defaultOfferId: "offer-cruise-1",
      defaultAncillaries: ["forex", "parking", "insurance"],
      audienceSplit: "78% Premier Couples · 22% Luxury Seekers"
    },
    henderson: {
      id: "henderson",
      name: "David & Claire Henderson",
      label: "David & Claire Henderson (Short-Lead Sun Seekers · Mosaic: Suburban Stability)",
      mosaicCohort: "Suburban Stability / Aspiring Homemakers",
      confidenceScore: 460,
      partySummary: "2 Adults, 1 Child (All-Inclusive Value)",
      partyMultiplier: 3,
      defaultOfferId: "offer-vista-1",
      defaultAncillaries: ["forex"],
      audienceSplit: "58% Value Sun Seekers · 42% Family All-Inc"
    }
  },

  offers: [
    {
      id: "offer-core-1",
      slotType: "CORE MOSAIC MATCH",
      ribbonClass: "ribbon-core",
      marginClass: "margin-core",
      isPreferredPartner: false,
      supplierId: "JET2HOL",
      hotelName: "Princesa Yaiza Suite Hotel Resort",
      destination: "Playa Blanca, Lanzarote",
      lat: 28.8643,
      lon: -13.8287,
      departureDate: "24 Oct 2026",
      nights: 7,
      boardBasis: "All Inclusive Plus",
      officialRating: "5★ Official Tour Op",
      officialStars: "★★★★★",
      googleRating: 4.7,
      googleReviews: "4,890",
      googleMapsUrl: "https://www.google.com/maps/search/?api=1&query=Princesa+Yaiza+Suite+Hotel+Resort+Playa+Blanca+Lanzarote",
      imageAssetId: "IMG-RESORT-4A91B2C8D1",
      headerGradient: "linear-gradient(135deg, #0284C7 0%, #0369A1 55%, #0F172A 100%)",
      pricePp: 799,
      totalBasketBase: 2397,
      marginLabel: "Std 11% Margin",
      sunScore: 95,
      destTempC: 27,
      tempDeltaC: 18,
      sunProbPct: 91,
      rainRiskPct: 5,
      uvIndex: 8,
      weatherHook: "Guaranteed 27°C southern Lanzarote micro-climate with 91% clear skies vs cold UK rain.",
      rationale: {
        jenkins: "Proven #1 Core Match for Boomerang Boarders; beachfront family suites & 5-min walk to Marina Rubicón.",
        smith: "Canary Islands favourite — ideal baseline to compare against Preferred Partner contract (DIR0001) or Mediterranean Cruise.",
        henderson: "Dependable Canary All-Inclusive with 8 restaurants and direct 25-min transfer from Arrecife (ACE)."
      },
      ensemble7Day: [
        { day: "Mon", icon: "☀️", temp: 27, prob: "92%" },
        { day: "Tue", icon: "☀️", temp: 27, prob: "94%" },
        { day: "Wed", icon: "🌤️", temp: 26, prob: "88%" },
        { day: "Thu", icon: "☀️", temp: 27, prob: "91%" },
        { day: "Fri", icon: "☀️", temp: 27, prob: "93%" },
        { day: "Sat", icon: "☀️", temp: 28, prob: "95%" },
        { day: "Sun", icon: "🌤️", temp: 26, prob: "90%" }
      ],
      pois: [
        {
          id: "poi-core1-1",
          category: "🍽️ DINING & TAPAS",
          name: "Lani's Grill & Sunset Marina Terrace (Marina Rubicón)",
          rating: "4.7★",
          reviews: "1,980",
          distance: "🚶 8 min waterfront walk",
          hook: "Yacht-side tapas & fresh Atlantic sea bass overlooking Marina Rubicón.",
          daySlot: "Day 1 Evening",
          defaultChecked: true
        },
        {
          id: "poi-core1-2",
          category: "🚤 SIGNATURE EXCURSION (UPSELL)",
          name: "Timanfaya National Park & Jameos del Agua Tour",
          rating: "4.8★",
          reviews: "29,400",
          distance: "🚐 20 min coach transfer",
          hook: "Geothermal Fire Mountains & lava caves — signature full-day excursion.",
          daySlot: "Day 2 Full Day",
          defaultChecked: true
        },
        {
          id: "poi-core1-3",
          category: "🏖️ BEACH & RELAXATION",
          name: "Playa de Papagayo Natural Cove",
          rating: "4.8★",
          reviews: "12,300",
          distance: "🚤 10 min water-taxi from Marina",
          hook: "Sheltered emerald-water volcanic cove ideal for snorkelling & family beach days.",
          daySlot: "Day 3 Morning",
          defaultChecked: false
        },
        {
          id: "poi-core1-4",
          category: "✨ CULTURE & HIDDEN GEM",
          name: "La Geria Volcanic Vineyard Wine Tasting",
          rating: "4.7★",
          reviews: "3,450",
          distance: "🚕 18 min scenic drive",
          hook: "Boutique Malvasía volcanic wine pairing in iconic stone-ringed craters.",
          daySlot: "Day 3 Afternoon",
          defaultChecked: false
        }
      ]
    },
    {
      id: "offer-vista-1",
      slotType: "💎 PREFERRED DIRECT CONTRACT · DIR0001",
      ribbonClass: "ribbon-vista",
      marginClass: "margin-vista",
      isPreferredPartner: true,
      supplierId: "DIR0001",
      hotelName: "Preferred Partner: Bahia Principe Sunlight Costa Adeje",
      destination: "Costa Adeje, Tenerife",
      lat: 28.0777,
      lon: -16.7297,
      departureDate: "24 Oct 2026",
      nights: 7,
      boardBasis: "24hr All Inclusive",
      officialRating: "4★ Official Tour Op",
      officialStars: "★★★★",
      googleRating: 4.7,
      googleReviews: "5,840",
      googleMapsUrl: "https://www.google.com/maps/search/?api=1&query=Bahia+Principe+Sunlight+Costa+Adeje+Tenerife",
      imageAssetId: "IMG-RESORT-9F2E7D41A6",
      headerGradient: "linear-gradient(135deg, #059669 0%, #047857 52%, #002B5C 100%)",
      pricePp: 779,
      totalBasketBase: 2337,
      marginLabel: "22% Margin (18–25% Tier)",
      sunScore: 97,
      destTempC: 27,
      tempDeltaC: 18,
      sunProbPct: 95,
      rainRiskPct: 4,
      uvIndex: 8,
      weatherHook: "Sheltered clifftop sun-trap averaging 27°C (+18°C warmer than UK) with uninterrupted Atlantic sun.",
      rationale: {
        jenkins: "In-house direct contract (DIR0001): saves Sarah £20 pp (£60 total) vs Core Match within the 22% margin tier!",
        smith: "Upgraded clifftop infinity pool & 3 à la carte restaurants — fresh Costa Adeje perspective with 22% margin tier.",
        henderson: "Best-in-class All-Inclusive value + free child place & private transfers included via direct contract."
      },
      ensemble7Day: [
        { day: "Mon", icon: "☀️", temp: 27, prob: "96%" },
        { day: "Tue", icon: "☀️", temp: 27, prob: "97%" },
        { day: "Wed", icon: "☀️", temp: 26, prob: "92%" },
        { day: "Thu", icon: "☀️", temp: 27, prob: "95%" },
        { day: "Fri", icon: "☀️", temp: 28, prob: "97%" },
        { day: "Sat", icon: "☀️", temp: 28, prob: "96%" },
        { day: "Sun", icon: "☀️", temp: 27, prob: "94%" }
      ],
      pois: [
        {
          id: "poi-vista1-1",
          category: "🍽️ DINING & TAPAS",
          name: "El Rincón de Juan Carlos (La Caleta)",
          rating: "4.8★",
          reviews: "2,640",
          distance: "🚕 7 min drive (3.1km)",
          hook: "Canarian tasting menu in picturesque La Caleta fishing village.",
          daySlot: "Day 1 Evening",
          defaultChecked: true
        },
        {
          id: "poi-vista1-2",
          category: "🚤 SIGNATURE EXCURSION (UPSELL)",
          name: "Freebird Luxury Catamaran Whale Watching",
          rating: "4.8★",
          reviews: "6,480",
          distance: "🚕 10 min transfer (Puerto Colón)",
          hook: "VIP sunbed catamaran cruise to Los Gigantes cliffs with drinks & swim stop included.",
          daySlot: "Day 2 Full Day",
          defaultChecked: true
        },
        {
          id: "poi-vista1-3",
          category: "🏖️ BEACH & RELAXATION",
          name: "Playa del Duque Golden Sand Cove",
          rating: "4.6★",
          reviews: "11,200",
          distance: "🚕 5 min shuttle (2.4km)",
          hook: "Upscale promenade with calm turquoise waters, boutique cafés & designer shopping.",
          daySlot: "Day 3 Morning",
          defaultChecked: true
        },
        {
          id: "poi-vista1-4",
          category: "✨ CULTURE & HIDDEN GEM",
          name: "Mount Teide Sunset & Stargazing Safari",
          rating: "4.9★",
          reviews: "5,310",
          distance: "🚐 Hotel Pick-up Included",
          hook: "Guided cable-car ascent with local wine tasting above the clouds.",
          daySlot: "Day 3 Afternoon",
          defaultChecked: false
        }
      ]
    },
    {
      id: "offer-core-2",
      slotType: "CORE AEGEAN SUN MATCH",
      ribbonClass: "ribbon-core",
      marginClass: "margin-core",
      isPreferredPartner: false,
      supplierId: "EASYJETHOL",
      hotelName: "Lindos Imperial Resort & Spa",
      destination: "Lindos, Rhodes",
      lat: 36.0914,
      lon: 28.0861,
      departureDate: "24 Oct 2026",
      nights: 7,
      boardBasis: "Ultra All Inclusive",
      officialRating: "5★ Official Tour Op",
      officialStars: "★★★★★",
      googleRating: 4.5,
      googleReviews: "3,420",
      googleMapsUrl: "https://www.google.com/maps/search/?api=1&query=Lindos+Imperial+Resort+Spa+Rhodes",
      imageAssetId: "IMG-RESORT-8E3B91C4A2",
      headerGradient: "linear-gradient(135deg, #0369A1 0%, #1E3A8A 55%, #0F172A 100%)",
      pricePp: 749,
      totalBasketBase: 2247,
      marginLabel: "Std 12% Margin",
      sunScore: 89,
      destTempC: 25,
      tempDeltaC: 16,
      sunProbPct: 86,
      rainRiskPct: 11,
      uvIndex: 6,
      weatherHook: "25°C Aegean sunshine along Kiotari Bay with crystal-clear swimming waters.",
      rationale: {
        jenkins: "Private beach cove + 6 waterslides & dine-around Greek tavernas for family sun seekers.",
        smith: "10 minutes from whitewashed Lindos Acropolis with adults-only infinity pool zone.",
        henderson: "Outstanding 5★ Aegean All-Inclusive pricing £50pp below Canary equivalents."
      },
      ensemble7Day: [
        { day: "Mon", icon: "☀️", temp: 25, prob: "86%" },
        { day: "Tue", icon: "☀️", temp: 25, prob: "88%" },
        { day: "Wed", icon: "🌤️", temp: 24, prob: "82%" },
        { day: "Thu", icon: "☀️", temp: 25, prob: "87%" },
        { day: "Fri", icon: "☀️", temp: 26, prob: "89%" },
        { day: "Sat", icon: "☀️", temp: 25, prob: "86%" },
        { day: "Sun", icon: "🌤️", temp: 24, prob: "84%" }
      ],
      pois: [
        {
          id: "poi-core2-1",
          category: "🍽️ DINING & TAPAS",
          name: "Mavrikos Rooftop Courtyard (Lindos Village)",
          rating: "4.7★",
          reviews: "1,890",
          distance: "🚕 10 min taxi to Lindos",
          hook: "Historic Rhodian fine taverna beneath the floodlit Acropolis.",
          daySlot: "Day 1 Evening",
          defaultChecked: true
        },
        {
          id: "poi-core2-2",
          category: "🚤 SIGNATURE EXCURSION (UPSELL)",
          name: "Symi Island & Panormitis High-Speed Yacht Day Trip",
          rating: "4.8★",
          reviews: "4,610",
          distance: "🚐 Resort Transfer Included",
          hook: "Pastel neoclassical harbour cruise + St George's Bay swim stop.",
          daySlot: "Day 2 Full Day",
          defaultChecked: true
        },
        {
          id: "poi-core2-3",
          category: "🏖️ BEACH & RELAXATION",
          name: "St Paul's Bay Heart-Shaped Lagoon",
          rating: "4.8★",
          reviews: "8,750",
          distance: "🚕 11 min drive (7.5km)",
          hook: "Enclosed turquoise bay framed by whitewashed chapel & limestone cliffs.",
          daySlot: "Day 3 Morning",
          defaultChecked: false
        },
        {
          id: "poi-core2-4",
          category: "✨ CULTURE & HIDDEN GEM",
          name: "Acropolis of Lindos Early-Bird Guided Ascent",
          rating: "4.8★",
          reviews: "19,200",
          distance: "🚕 10 min drive",
          hook: "Doric temple of Athena Lindia overlooking two Aegean bays.",
          daySlot: "Day 3 Afternoon",
          defaultChecked: false
        }
      ]
    },
    {
      id: "offer-vista-2",
      slotType: "💎 PREFERRED DIRECT CONTRACT · DIR0002",
      ribbonClass: "ribbon-vista",
      marginClass: "margin-vista",
      isPreferredPartner: true,
      supplierId: "DIR0002",
      hotelName: "Preferred Partner: Constantinou Bros Athena Beach",
      destination: "Paphos, Cyprus",
      lat: 34.7720,
      lon: 32.4297,
      departureDate: "25 Oct 2026",
      nights: 7,
      boardBasis: "Ultra All Inclusive",
      officialRating: "4★ Superior Official",
      officialStars: "★★★★+",
      googleRating: 4.7,
      googleReviews: "3,980",
      googleMapsUrl: "https://www.google.com/maps/search/?api=1&query=Constantinou+Bros+Athena+Beach+Hotel+Paphos",
      imageAssetId: "IMG-RESORT-5D7A2C19E4",
      headerGradient: "linear-gradient(135deg, #059669 0%, #065F46 55%, #001E42 100%)",
      pricePp: 849,
      totalBasketBase: 2547,
      marginLabel: "23% Direct Margin",
      sunScore: 94,
      destTempC: 27,
      tempDeltaC: 18,
      sunProbPct: 91,
      rainRiskPct: 7,
      uvIndex: 7,
      weatherHook: "Eastern Med late-season sun powerhouse averaging 27°C in Paphos with warm 24°C sea.",
      rationale: {
        jenkins: "Beachfront oasis with splash park, bowling greens & 23% in-house direct margin tier.",
        smith: "Elite Adults-Only wing, private beach cabanas & flat coastal path to Paphos Harbour.",
        henderson: "Includes private airport taxi transfers + 23% in-house direct margin tier."
      },
      ensemble7Day: [
        { day: "Mon", icon: "☀️", temp: 27, prob: "91%" },
        { day: "Tue", icon: "☀️", temp: 27, prob: "92%" },
        { day: "Wed", icon: "☀️", temp: 26, prob: "89%" },
        { day: "Thu", icon: "☀️", temp: 27, prob: "91%" },
        { day: "Fri", icon: "☀️", temp: 28, prob: "93%" },
        { day: "Sat", icon: "☀️", temp: 27, prob: "91%" },
        { day: "Sun", icon: "☀️", temp: 27, prob: "90%" }
      ],
      pois: [
        {
          id: "poi-vista2-1",
          category: "🍽️ DINING & TAPAS",
          name: "7 St. Georges Traditional Cypriot Meze",
          rating: "4.7★",
          reviews: "2,150",
          distance: "🚕 6 min drive (2.2km)",
          hook: "Farm-to-table organic seasonal Cypriot meze & local dessert wine.",
          daySlot: "Day 1 Evening",
          defaultChecked: true
        },
        {
          id: "poi-vista2-2",
          category: "🚤 SIGNATURE EXCURSION (UPSELL)",
          name: "Akamas Peninsula Blue Lagoon VIP Yacht Cruise",
          rating: "4.8★",
          reviews: "5,120",
          distance: "🚐 Hotel Pick-up to Latchi Harbour",
          hook: "Crystal-clear Blue Lagoon swim + BBQ lunch & local refreshments.",
          daySlot: "Day 2 Full Day",
          defaultChecked: true
        },
        {
          id: "poi-vista2-3",
          category: "🏖️ BEACH & RELAXATION",
          name: "Coral Bay Golden Horseshoe Beach",
          rating: "4.6★",
          reviews: "9,840",
          distance: "🚕 18 min coastal drive",
          hook: "Blue-Flag golden sand bay sheltered by limestone headlands.",
          daySlot: "Day 3 Morning",
          defaultChecked: false
        },
        {
          id: "poi-vista2-4",
          category: "✨ CULTURE & HIDDEN GEM",
          name: "Kato Paphos Roman Mosaics & Harbour Walk",
          rating: "4.7★",
          reviews: "14,300",
          distance: "🚶 20 min flat coastal promenade walk",
          hook: "Ancient mosaics right by historic Paphos Castle.",
          daySlot: "Day 3 Afternoon",
          defaultChecked: false
        }
      ]
    },
    {
      id: "offer-core-3",
      slotType: "🌟 TURKISH RIVIERA LUXURY",
      ribbonClass: "ribbon-lh",
      marginClass: "margin-lh",
      isPreferredPartner: false,
      supplierId: "JET2INDULGE",
      hotelName: "Delphin Imperial Resort",
      destination: "Lara Beach, Antalya",
      lat: 36.8550,
      lon: 30.8572,
      departureDate: "24 Oct 2026",
      nights: 7,
      boardBasis: "Ultra All Inclusive",
      officialRating: "5★ Official Tour Op",
      officialStars: "★★★★★",
      googleRating: 4.8,
      googleReviews: "7,640",
      googleMapsUrl: "https://www.google.com/maps/search/?api=1&query=Delphin+Imperial+Lara+Beach+Antalya",
      imageAssetId: "IMG-RESORT-2B8F6A14C9",
      headerGradient: "linear-gradient(135deg, #7C3AED 0%, #5B21B6 55%, #002B5C 100%)",
      pricePp: 899,
      totalBasketBase: 2697,
      marginLabel: "Indulgence Tier",
      sunScore: 92,
      destTempC: 27,
      tempDeltaC: 18,
      sunProbPct: 89,
      rainRiskPct: 9,
      uvIndex: 7,
      weatherHook: "27°C Turkish Riviera sunshine on Lara Beach with heated outdoor pools & private pier.",
      rationale: {
        jenkins: "Unbeatable 5★ Lara Beach resort with aquapark & 9 à la carte restaurants.",
        smith: "VIP pier cabanas, champagne lounge & 15-min transfer from Antalya Airport (AYT).",
        henderson: "True Ultra All-Inclusive — 24hr dining & zero extra spend in resort."
      },
      ensemble7Day: [
        { day: "Mon", icon: "☀️", temp: 27, prob: "90%" },
        { day: "Tue", icon: "☀️", temp: 27, prob: "91%" },
        { day: "Wed", icon: "🌤️", temp: 26, prob: "85%" },
        { day: "Thu", icon: "☀️", temp: 27, prob: "89%" },
        { day: "Fri", icon: "☀️", temp: 27, prob: "91%" },
        { day: "Sat", icon: "☀️", temp: 26, prob: "88%" },
        { day: "Sun", icon: "🌤️", temp: 26, prob: "87%" }
      ],
      pois: [
        {
          id: "poi-core3-1",
          category: "🍽️ DINING & TAPAS",
          name: "Panoramic Mediterranean Restaurant",
          rating: "4.7★",
          reviews: "6,820",
          distance: "🚕 18 min taxi to Konyaaltı Cliffs",
          hook: "Iconic culinary institution overlooking coastal mountain ranges.",
          daySlot: "Day 1 Evening",
          defaultChecked: true
        },
        {
          id: "poi-core3-2",
          category: "🚤 SIGNATURE EXCURSION (UPSELL)",
          name: "Lower Düden Waterfalls Sunset Catamaran & Old Town",
          rating: "4.8★",
          reviews: "16,400",
          distance: "🚕 10 min coastal drive (Lara Cliffs)",
          hook: "40m waterfall plunging straight into the turquoise Mediterranean.",
          daySlot: "Day 2 Full Day",
          defaultChecked: true
        },
        {
          id: "poi-core3-3",
          category: "🏖️ BEACH & RELAXATION",
          name: "Lara Beach Blue-Flag Private Pier & Pavilions",
          rating: "4.7★",
          reviews: "5,490",
          distance: "🚶 Direct Resort Beachfront",
          hook: "Over-water VIP waiter service pavilions along 2km of golden sand.",
          daySlot: "Day 3 Morning",
          defaultChecked: false
        },
        {
          id: "poi-core3-4",
          category: "✨ CULTURE & HIDDEN GEM",
          name: "Historic Roman Harbour & Monument Walk",
          rating: "4.8★",
          reviews: "24,100",
          distance: "🚕 20 min drive",
          hook: "Historic architecture, boutique shopping & Roman harbour yachts.",
          daySlot: "Day 3 Afternoon",
          defaultChecked: false
        }
      ]
    },
    {
      id: "offer-cruise-1",
      slotType: "🚢 CRUISE WILDCARD",
      ribbonClass: "ribbon-cruise",
      marginClass: "margin-cruise",
      isPreferredPartner: false,
      supplierId: "POCRUISES",
      hotelName: "Premier Cruises · Palma & Western Med Fly-Cruise",
      destination: "Palma de Mallorca & Western Mediterranean",
      lat: 39.5696,
      lon: 2.6502,
      departureDate: "25 Oct 2026",
      nights: 7,
      boardBasis: "Full Board + Select Drinks",
      officialRating: "5★ Official Ship Tier",
      officialStars: "★★★★★",
      googleRating: 4.5,
      googleReviews: "2,310",
      googleMapsUrl: "https://www.google.com/maps/search/?api=1&query=Port+de+Palma+Mallorca+Cruise+Terminal",
      imageAssetId: "IMG-RESORT-7C1D5E89B3",
      headerGradient: "linear-gradient(135deg, #4F46E5 0%, #3730A3 55%, #002B5C 100%)",
      pricePp: 929,
      totalBasketBase: 2787,
      marginLabel: "16% Cruise Margin",
      sunScore: 88,
      destTempC: 24,
      tempDeltaC: 15,
      sunProbPct: 84,
      rainRiskPct: 12,
      uvIndex: 6,
      weatherHook: "Follows the Mediterranean sun from Palma across 4 iconic ports with retractable glass pool roof.",
      rationale: {
        jenkins: "High-repeat family wildcard: onboard entertainment & 4 Med ports in 1 unpacking.",
        smith: "#1 T+7 Re-Book Upgrade: Sea-View Balcony Cabin from Palma + on-board credit allowance.",
        henderson: "Gratuities, flights & transfers included — clear pricing across 12 onboard dining venues."
      },
      ensemble7Day: [
        { day: "Mon", icon: "☀️", temp: 24, prob: "85%" },
        { day: "Tue", icon: "☀️", temp: 24, prob: "86%" },
        { day: "Wed", icon: "🌤️", temp: 23, prob: "81%" },
        { day: "Thu", icon: "☀️", temp: 24, prob: "84%" },
        { day: "Fri", icon: "☀️", temp: 25, prob: "87%" },
        { day: "Sat", icon: "☀️", temp: 24, prob: "85%" },
        { day: "Sun", icon: "☀️", temp: 24, prob: "84%" }
      ],
      pois: [
        {
          id: "poi-cruise-1",
          category: "🍽️ DINING & TAPAS",
          name: "Palma Old Town Waterfront Tapas Bar",
          rating: "4.7★",
          reviews: "2,840",
          distance: "🚕 10 min from Palma Cruise Terminal",
          hook: "Bustling Mallorcan tapas & local wines by the port.",
          daySlot: "Day 1 Port Stop",
          defaultChecked: true
        },
        {
          id: "poi-cruise-2",
          category: "🚤 SIGNATURE EXCURSION (UPSELL)",
          name: "Vintage Sóller Mountain Railway Tour",
          rating: "4.7★",
          reviews: "18,900",
          distance: "🚌 Shore Excursion Transfer",
          hook: "Scenic wooden mountain railway through citrus valley groves.",
          daySlot: "Day 2 Port Stop",
          defaultChecked: true
        },
        {
          id: "poi-cruise-3",
          category: "🏖️ BEACH & RELAXATION",
          name: "Palma Bay Beach Club",
          rating: "4.5★",
          reviews: "4,500",
          distance: "🚕 8 min taxi from Cruise Pier",
          hook: "Seafront lounge beds overlooking the cathedral and bay.",
          daySlot: "Day 3 Morning",
          defaultChecked: false
        },
        {
          id: "poi-cruise-4",
          category: "✨ CULTURE & HIDDEN GEM",
          name: "Catedral-Basílica de Santa María de Mallorca",
          rating: "4.8★",
          reviews: "41,200",
          distance: "🚕 8 min transfer from Pier",
          hook: "Rooftop terrace tour overlooking the historic harbour.",
          daySlot: "Day 3 Afternoon",
          defaultChecked: false
        }
      ]
    }
  ],

  ancillaries: [
    {
      id: "forex",
      icon: "💶",
      title: "In-Branch Foreign Exchange (EUR / USD)",
      gapStatus: "0 Historical FX Orders detected · Branch HasForex = Yes",
      priceGbp: 650,
      priceLabel: "+£650 Currency Order"
    },
    {
      id: "parking",
      icon: "🅿️",
      title: "Airport Parking & Priority Fast-Track",
      gapStatus: "CarParkCount = 0 on Customer profile",
      priceGbp: 94,
      priceLabel: "+£94 Meet & Greet"
    },
    {
      id: "insurance",
      icon: "🛡️",
      title: "Comprehensive Travel Protection Policy",
      gapStatus: "InsuranceCount = 0 on booking record",
      priceGbp: 118,
      priceLabel: "+£118 Family Policy"
    }
  ],

  dialects: {
    northeast: {
      id: "northeast",
      label: "North East (Newcastle — Regional Warmth)",
      headlinePrefix: "🌧️ Ready to swap {ukTemp}°C UK rain for {destTemp}°C sunshine?",
      bodyTemplate: "Why shiver in {ukTemp}°C {ukCond} when {dest} is basking in {destTemp}°C glorious sunshine (+{tempDiff}°C warmer this week!)? ☀️✈️\n\nFly direct from {airport} to {hotel} ({officialRating}) — {nights} nights {board} from just £{pricePp}pp! Top-rated by guests on Google Maps ({googleRating}★ from {googleReviews} reviews) with {poi1} and {poi2} right on your doorstep.\n\nConnect with our {branchName} branch team today and let's get your sunshine booked! ☀️🌴",
      hashtags: "#EnterpriseTravel #NewcastleAirport #WinterSun #HolidayDeals #WeatherNext #VerifiedOperator"
    },
    scotland: {
      id: "scotland",
      label: "Scotland (Glasgow — West Coast Warmth)",
      headlinePrefix: "🏴󠁧󠁢󠁳󠁣󠁴󠁿 Leave the dreich {ukTemp}°C weather behind — jet straight to {destTemp}°C sun!",
      bodyTemplate: "Leave the heavy coat behind! While it's {ukTemp}°C and {ukRain}% rain in {city}, our live WeatherNext forecast shows {destTemp}°C golden sunshine in {dest} (+{tempDiff}°C warmer!). ☀️🌴\n\nJet off direct from {airport} to the stunning {hotel} ({officialRating}) for {nights} nights {board} from £{pricePp}pp. Exceptional value with {poi1} and {poi2} minutes away!\n\nVisit our {branchName} team today or message us directly to lock in this package! ✈️💛",
      hashtags: "#EnterpriseTravel #GlasgowAirport #WinterSun #HolidayDeals #VerifiedOperator"
    },
    northwest: {
      id: "northwest",
      label: "North West (Manchester — Bold & Direct)",
      headlinePrefix: "☀️ Swap {ukTemp}°C Manchester showers for {destTemp}°C sun in {dest}!",
      bodyTemplate: "Warm sunshine calling! ☀️ It's {ukTemp}°C in {city} today vs a pleasant {destTemp}°C on our 7-day WeatherNext forecast in {dest} (+{tempDiff}°C thermal uplift!).\n\nFly direct from {airport} to {hotel} ({officialRating}) — {nights} nights {board} from £{pricePp}pp. Guests rate it {googleRating}★ on Google Maps across {googleReviews} reviews, plus you're right near {poi1} & {poi2}!\n\nDrop into our {branchName} branch or contact our advisors now! ✈️💛",
      hashtags: "#EnterpriseTravel #ManchesterAirport #HolidayDeals #VerifiedOperator"
    },
    standard: {
      id: "standard",
      label: "UK Standard (Corporate Brand Voice)",
      headlinePrefix: "☀️ Trade {ukTemp}°C UK skies for {destTemp}°C sunshine in {dest}!",
      bodyTemplate: "Looking for guaranteed warmth? Our live 7-day WeatherNext forecast shows {destTemp}°C sunshine in {dest} — a full +{tempDiff}°C warmer than {city} today! ☀️✈️\n\nDeparting direct from {airport}, enjoy {nights} nights {board} at {hotel} ({officialRating}) from £{pricePp}pp. Rated {googleRating}★ on Google Maps ({googleReviews} reviews) and ideally located for {poi1} and {poi2}.\n\nVisit our travel specialists at {branchName} today! 💛✈️",
      hashtags: "#EnterpriseTravel #TailoredHolidays #SunSeeker #VerifiedOperator"
    }
  },

  welcomeHomeQueue: [
    {
      bookingRef: "BK-994821",
      customerName: "Mr & Mrs Smith",
      personaId: "smith",
      returnedDaysAgo: 3,
      returnedFrom: "GF Fañabé, Tenerife",
      mosaicBadge: "Mosaic: Prestige Positions (Group A)",
      confidence: 495,
      priorSpendGbp: 2840,
      upsellHook: "Loved Costa Adeje climate; pitch Premier Western Med Fly-Cruise or Direct Contract (DIR0001) 2027 early-bird.",
      callLogged: false
    },
    {
      bookingRef: "BK-993104",
      customerName: "Mrs Sarah Jenkins",
      personaId: "jenkins",
      returnedDaysAgo: 5,
      returnedFrom: "Alcudia Pins, Mallorca",
      mosaicBadge: "Mosaic: Boomerang Boarders",
      confidence: 482,
      priorSpendGbp: 3120,
      upsellHook: "October half-term sun seeker; pitch Direct Contract Bahia Principe (DIR0001) + water park excursion.",
      callLogged: false
    },
    {
      bookingRef: "BK-991850",
      customerName: "David & Claire Henderson",
      personaId: "henderson",
      returnedDaysAgo: 6,
      returnedFrom: "Premier Cruise, Norwegian Fjords",
      mosaicBadge: "Mosaic: Suburban Stability",
      confidence: 460,
      priorSpendGbp: 3690,
      upsellHook: "Ready to trade cool weather for 27°C Canary sun or Delphin Imperial Antalya Ultra All-Inclusive.",
      callLogged: false
    }
  ],

  balanceDueQueue: [
    {
      bookingRef: "BK-882410",
      customerName: "Mr Callum Robson",
      departsDate: "18 Nov 2026",
      destination: "Costa Adeje, Tenerife",
      isActiveDirectDebit: "N",
      dueInDays: 2,
      dueDateLabel: "19 Oct 2026",
      outstandingGbp: 1480.00,
      grossGbp: 2100.00,
      reminded: false
    },
    {
      bookingRef: "BK-883902",
      customerName: "Miss Kirsty MacLeod",
      departsDate: "24 Nov 2026",
      destination: "Playa Blanca, Lanzarote",
      isActiveDirectDebit: "N",
      dueInDays: 4,
      dueDateLabel: "21 Oct 2026",
      outstandingGbp: 1920.00,
      grossGbp: 2420.00,
      reminded: false
    },
    {
      bookingRef: "BK-885119",
      customerName: "Mr & Mrs Patel",
      departsDate: "02 Dec 2026",
      destination: "Barbados Fly-Cruise",
      isActiveDirectDebit: "Y",
      dueInDays: 9,
      dueDateLabel: "26 Oct 2026",
      outstandingGbp: 2650.00,
      grossGbp: 3450.00,
      reminded: false
    }
  ]
};

window.ENTERPRISE_DATA = window.A2UI_DATA;
