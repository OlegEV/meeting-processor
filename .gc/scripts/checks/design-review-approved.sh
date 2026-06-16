#!/usr/bin/env bash
# Check script for github-issue-fix design-review retry loops.

set -euo pipefail

BEAD_ID="${GC_BEAD_ID:-}"
if [ -z "$BEAD_ID" ]; then
    echo "ERROR: GC_BEAD_ID not set" >&2
    exit 1
fi

BEAD_JSON=$(bd show "$BEAD_ID" --json 2>/dev/null)
ROOT_ID=$(printf '%s\n' "$BEAD_JSON" | jq -r 'if type == "array" then (.[0].metadata["gc.root_bead_id"] // "") else (.metadata["gc.root_bead_id"] // "") end')
ATTEMPT=$(printf '%s\n' "$BEAD_JSON" | jq -r 'if type == "array" then (.[0].metadata["gc.attempt"] // "") else (.metadata["gc.attempt"] // "") end')
SCOPE_REF=$(printf '%s\n' "$BEAD_JSON" | jq -r 'if type == "array" then (.[0].metadata["gc.scope_ref"] // .[0].metadata["gc.step_ref"] // "") else (.metadata["gc.scope_ref"] // .metadata["gc.step_ref"] // "") end')
STEP_ID=$(printf '%s\n' "$BEAD_JSON" | jq -r 'if type == "array" then (.[0].metadata["gc.step_id"] // "") else (.metadata["gc.step_id"] // "") end')
if [ -z "$ROOT_ID" ]; then
    echo "ERROR: missing gc.root_bead_id on $BEAD_ID" >&2
    exit 1
fi

VERDICT=$(
    bd list --all --metadata-field "gc.root_bead_id=$ROOT_ID" --json --limit=0 2>/dev/null |
        jq -r --arg root "$ROOT_ID" --arg attempt "$ATTEMPT" --arg scope "$SCOPE_REF" --arg step "$STEP_ID" '
            [
              .[]
              | select(.metadata["gc.root_bead_id"] == $root)
              | select(($attempt == "") or ((.metadata["gc.attempt"] // "") == $attempt))
              | select(
                  if $attempt != "" and $scope != "" then
                    ((.metadata["gc.scope_ref"] // "") == $scope)
                  elif $step != "" then
                    ((.metadata["gc.ralph_step_id"] // "") == $step) or
                    (((.metadata["gc.scope_ref"] // "") | startswith($step + ".iteration.")))
                  elif $scope != "" then
                    ((.metadata["gc.scope_ref"] // "") == $scope)
                  else
                    ((.metadata["gc.continuation_group"] // "") == "design-review-fixes")
                  end
                )
              | {attempt: ((.metadata["gc.attempt"] // "0") | tonumber? // 0), updated_at: (.updated_at // ""), verdict: (.metadata["design_review.verdict"] // "")}
              | select(.verdict != "")
            ] | sort_by(.attempt, .updated_at) | last.verdict // ""
        '
)

case "$VERDICT" in
    done|approved|pass)
        echo "Design review approved"
        exit 0
        ;;
    iterate|fail|retry|"")
        echo "Design review needs another pass"
        exit 1
        ;;
    *)
        echo "Unknown design-review verdict: $VERDICT" >&2
        exit 1
        ;;
esac
