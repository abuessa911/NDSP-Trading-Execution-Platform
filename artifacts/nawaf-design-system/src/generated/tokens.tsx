/* GENERATED FROM tokens.json -- DO NOT EDIT. Run scripts/build-tokens.mjs. */
// Portable design tokens (colors as hex). Web consumes the theme via
// src/index.css; mobile (Expo) and any other platform import this object so the
// whole product shares one source of truth.
export const tokens = {
  "color": {
    "light": {
      "background": "#f3f7fa",
      "foreground": "#182c40",
      "border": "#becbd6",
      "card": "#ffffff",
      "cardForeground": "#182c40",
      "popover": "#ffffff",
      "popoverForeground": "#182c40",
      "primary": "#12685b",
      "primaryForeground": "#ffffff",
      "secondary": "#e3edf3",
      "secondaryForeground": "#182c40",
      "muted": "#eaf0f5",
      "mutedForeground": "#526779",
      "accent": "#daefea",
      "accentForeground": "#12685b",
      "destructive": "#a63626",
      "destructiveForeground": "#ffffff",
      "input": "#718699",
      "ring": "#12685b",
      "chart1": "#12685b",
      "chart2": "#1b754e",
      "chart3": "#a63626",
      "chart4": "#865519",
      "chart5": "#365faf",
      "sidebar": "#eaf0f5",
      "sidebarForeground": "#182c40",
      "sidebarBorder": "#becbd6",
      "sidebarPrimary": "#12685b",
      "sidebarPrimaryForeground": "#ffffff",
      "sidebarAccent": "#daefea",
      "sidebarAccentForeground": "#12685b",
      "sidebarRing": "#12685b"
    },
    "dark": {
      "background": "#080c11",
      "foreground": "#e6eef6",
      "border": "#283747",
      "card": "#131d29",
      "cardForeground": "#e6eef6",
      "popover": "#182432",
      "popoverForeground": "#e6eef6",
      "primary": "#72d7c6",
      "primaryForeground": "#0a2d2c",
      "secondary": "#1d2c3b",
      "secondaryForeground": "#e6eef6",
      "muted": "#182432",
      "mutedForeground": "#98aabd",
      "accent": "#1a3538",
      "accentForeground": "#9ce7da",
      "destructive": "#ff7a66",
      "destructiveForeground": "#080c11",
      "input": "#708397",
      "ring": "#72d7c6",
      "chart1": "#72d7c6",
      "chart2": "#4fd39a",
      "chart3": "#ff7a66",
      "chart4": "#f1bc71",
      "chart5": "#7aa7ff",
      "sidebar": "#0e1722",
      "sidebarForeground": "#e6eef6",
      "sidebarBorder": "#283747",
      "sidebarPrimary": "#72d7c6",
      "sidebarPrimaryForeground": "#0a2d2c",
      "sidebarAccent": "#1a3538",
      "sidebarAccentForeground": "#9ce7da",
      "sidebarRing": "#72d7c6"
    }
  },
  "fontFamily": {
    "sans": [
      "Avenir Next",
      "Segoe UI Variable",
      "Trebuchet MS",
      "system-ui",
      "sans-serif"
    ],
    "serif": [
      "Georgia",
      "serif"
    ],
    "mono": [
      "SFMono-Regular",
      "Consolas",
      "Liberation Mono",
      "monospace"
    ]
  },
  "radius": "0.4375rem",
  "spacing": "0.25rem",
  "sizing": {
    "controlSm": "1.75rem",
    "controlMd": "2.1875rem",
    "controlLg": "2.75rem",
    "iconXs": "0.6875rem",
    "iconSm": "0.8125rem",
    "iconMd": "1rem",
    "drawerWidth": "28.75rem",
    "chartHeight": "15rem",
    "lineChartHeight": "8.75rem",
    "barsHeight": "6.875rem",
    "ringSize": "6rem",
    "meterHeight": "0.375rem",
    "meterMinWidth": "2.5rem",
    "kvLabelMin": "8.125rem",
    "contentMax": "64rem",
    "navWidth": "15.625rem",
    "focusWidth": "0.125rem",
    "focusOffset": "0.125rem",
    "bannerTextBasis": "15rem",
    "errorTextBasis": "12.5rem",
    "ringLabelSize": "1.125rem",
    "searchMinWidth": "13.75rem",
    "drawerSlideOffset": "1.875rem",
    "textareaMin": "3.75rem",
    "selectMin": "8rem",
    "drawerHandle": "6.25rem",
    "nudgeIndicator": "0.0625rem",
    "nudgeCheckbox": "0.125rem",
    "nudgeAlert": "0.1875rem",
    "switchTravel": "1rem",
    "dialogMax": "85vh",
    "chartMarginTop": "0.9375rem",
    "chartMarginEnd": "0.625rem",
    "chartAxisWidth": "4.25rem",
    "chartTick": "0.625rem",
    "navSlide": "13rem",
    "emptyIcon": "1.625rem",
    "errorIcon": "1.375rem",
    "searchIcon": "0.875rem"
  },
  "type": {
    "micro": "0.5625rem",
    "caption": "0.625rem",
    "small": "0.6875rem",
    "bodySm": "0.75rem",
    "body": "0.875rem",
    "heading": "1.0625rem",
    "kpi": "1.3125rem",
    "display": "1.875rem"
  },
  "motion": {
    "durationFast": "0.15s",
    "durationBase": "0.2s",
    "durationShimmer": "1.4s",
    "easingOut": "ease-out",
    "durationSheetOpen": "0.5s",
    "durationSheetClose": "0.3s",
    "durationNavIcon": "0.3s"
  },
  "zIndex": {
    "sticky": 11,
    "scrim": 40,
    "drawer": 41,
    "overlay": 50,
    "toast": 60
  },
  "breakpoint": {
    "sm": "740px",
    "md": "1050px",
    "wide": "1800px"
  }
} as const;

export type Tokens = typeof tokens;
export default tokens;
