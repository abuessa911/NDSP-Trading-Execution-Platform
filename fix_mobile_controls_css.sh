#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_mobile_controls_css_$STAMP"
mkdir -p "$BACKUP_DIR"

cp frontend/app/globals.css "$BACKUP_DIR/globals.css"

cat >> frontend/app/globals.css <<'CSS'

/* FINAL mobile-safe global controls override */
.global-controls {
  pointer-events: none !important;
}

.global-home-button,
.global-language-switcher {
  pointer-events: auto !important;
  position: fixed !important;
  top: calc(env(safe-area-inset-top, 0px) + 10px) !important;
  bottom: auto !important;
  width: auto !important;
  max-width: 128px !important;
  min-width: 0 !important;
  height: 38px !important;
  min-height: 38px !important;
  max-height: 38px !important;
  padding: 0 10px !important;
  border-radius: 999px !important;
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 7px !important;
  overflow: hidden !important;
  white-space: nowrap !important;
  line-height: 1 !important;
  transform: none !important;
}

.global-home-button {
  left: 10px !important;
  right: auto !important;
}

.global-language-switcher {
  right: 10px !important;
  left: auto !important;
}

.global-home-button span,
.global-language-switcher span {
  width: 26px !important;
  min-width: 26px !important;
  max-width: 26px !important;
  height: 26px !important;
  min-height: 26px !important;
  max-height: 26px !important;
  padding: 0 !important;
  border-radius: 999px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  line-height: 1 !important;
  font-size: 12px !important;
}

.global-home-button b,
.global-language-switcher b {
  display: inline-block !important;
  font-size: 12px !important;
  line-height: 1 !important;
  white-space: nowrap !important;
}

body:has(.global-controls) .container {
  padding-top: 68px;
}

@media (max-width: 700px) {
  .global-home-button,
  .global-language-switcher {
    top: calc(env(safe-area-inset-top, 0px) + 8px) !important;
    height: 34px !important;
    min-height: 34px !important;
    max-height: 34px !important;
    padding: 0 8px !important;
    max-width: 102px !important;
    z-index: 10000 !important;
  }

  .global-home-button {
    left: 8px !important;
  }

  .global-language-switcher {
    right: 8px !important;
  }

  .global-home-button span,
  .global-language-switcher span {
    width: 23px !important;
    min-width: 23px !important;
    max-width: 23px !important;
    height: 23px !important;
    min-height: 23px !important;
    max-height: 23px !important;
    font-size: 11px !important;
  }

  .global-home-button b,
  .global-language-switcher b {
    font-size: 11px !important;
  }

  body:has(.global-controls) .container {
    padding-top: 58px !important;
  }
}

@media (max-width: 390px) {
  .global-home-button b,
  .global-language-switcher b {
    display: none !important;
  }

  .global-home-button,
  .global-language-switcher {
    width: 38px !important;
    max-width: 38px !important;
    padding: 0 !important;
  }
}
CSS

docker compose up -d --build frontend

echo "✅ Mobile controls fixed"
echo "افتح الموقع ثم اعمل Refresh قوي"
