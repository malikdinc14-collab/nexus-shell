#!/usr/bin/env bash
# core/hud/modules/school.sh
# HUD Provider for the School Learner State.

STATE_FILE="/Users/Shared/Projects/school/learners/local_user/student_state.yaml"

if [[ -f "$STATE_FILE" ]]; then
    # Simple extraction using grep/awk since yq might not be installed
    # We want tier_1_claims count or similar
    tier_1_count=$(grep -A 10 "tier_1_claims:" "$STATE_FILE" | grep "-" | grep -v "^--" | wc -l | xargs)
    tier_2_count=$(grep -A 100 "tier_2_practiced:" "$STATE_FILE" | grep ":" | grep -v "tier_2_practiced" | grep -v "completed_at" | grep -v "score" | grep -v "source" | wc -l | xargs)
    
    label="T1:$tier_1_count T2:$tier_2_count"
    
    echo "{\"label\": \"$label\", \"color\": \"BLUE\"}"
else
    exit 0
fi
