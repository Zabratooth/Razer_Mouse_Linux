#!/bin/bash
# =============================================================================
# toggle_keys.sh
# Wechselt die Loop-Tasten zwischen Platzhalter (t/u) und WoW (F9/F10)
# =============================================================================

KEYMAP="$HOME/.naga/keyMapWayland.txt"

# Aktuellen Modus erkennen
if grep -q "dotool=key t" "$KEYMAP"; then
    # Wechsel zu F9/F10
    sed -i 's/dotool=key t/dotool=key F9/g' "$KEYMAP"
    sed -i 's/dotool=key u/dotool=key F10/g' "$KEYMAP"
    echo "✓ Modus: WoW (F9 / F10)"
else
    # Wechsel zu Platzhalter
    sed -i 's/dotool=key F9/dotool=key t/g' "$KEYMAP"
    sed -i 's/dotool=key F10/dotool=key u/g' "$KEYMAP"
    echo "✓ Modus: Test (t / u)"
fi

# naga neu starten
naga stop 2>/dev/null
sleep 1
naga start
echo "✓ naga neu gestartet"
