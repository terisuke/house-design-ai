#!/bin/bash
# Vertex AI ジョブモニタリングスクリプト

JOB_ID=${1:-4921829386442768384}
PROJECT_ID=${2:-yolov8environment}
REGION=${3:-asia-northeast1}

if [ -z "$1" ]; then
    echo "Usage: $0 <JOB_ID> [PROJECT_ID] [REGION]"
    echo "Example: $0 4921829386442768384 yolov8environment asia-northeast1"
    echo ""
    echo "To find recent jobs:"
    echo "gcloud ai custom-jobs list --region=$REGION --project=$PROJECT_ID --limit=5 --sort-by=createTime"
    exit 1
fi

echo "Monitoring Vertex AI Job: $JOB_ID"
echo "Project: $PROJECT_ID, Region: $REGION"
echo "========================================="

# Get job details including container image URI
echo "Fetching job details..."
JOB_DETAILS=$(gcloud ai custom-jobs describe $JOB_ID --region=$REGION --project=$PROJECT_ID --format=json 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "Error: Failed to fetch job details. Please check job ID, project, and region."
    exit 1
fi

# Extract and display container image URI
CONTAINER_IMAGE=$(echo "$JOB_DETAILS" | jq -r '.jobSpec.workerPoolSpecs[0].containerSpec.imageUri // "Not found"')
echo "Container Image URI: $CONTAINER_IMAGE"
echo "========================================="

# Track preparation time for stuck job detection
PREP_START_TIME=$(date +%s)
MAX_PREP_TIME=1800  # 30 minutes in seconds
INTERNAL_ERROR_COUNT=0
MAX_INTERNAL_ERRORS=3

while true; do
    # ジョブステータスを取得
    STATUS=$(gcloud ai custom-jobs describe $JOB_ID --region=$REGION --project=$PROJECT_ID --format="value(state)" 2>/dev/null)
    
    # Get current time for preparation time check
    CURRENT_TIME=$(date +%s)
    ELAPSED_TIME=$((CURRENT_TIME - PREP_START_TIME))
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Job Status: $STATUS (Elapsed: ${ELAPSED_TIME}s)"
    
    # 終了状態をチェック
    if [[ "$STATUS" == "JOB_STATE_SUCCEEDED" ]]; then
        echo "✅ Job completed successfully!"
        break
    elif [[ "$STATUS" == "JOB_STATE_FAILED" ]] || [[ "$STATUS" == "JOB_STATE_CANCELLED" ]]; then
        echo "❌ Job failed or cancelled!"
        # エラーメッセージを取得
        ERROR_MSG=$(gcloud ai custom-jobs describe $JOB_ID --region=$REGION --project=$PROJECT_ID --format="get(error.message)" 2>/dev/null)
        echo "Error: $ERROR_MSG"
        
        # Check for internal error pattern
        if [[ "$ERROR_MSG" == *"Internal error occurred for the current attempt"* ]]; then
            INTERNAL_ERROR_COUNT=$((INTERNAL_ERROR_COUNT + 1))
            echo "⚠️  Internal error detected (Count: $INTERNAL_ERROR_COUNT/$MAX_INTERNAL_ERRORS)"
            if [ $INTERNAL_ERROR_COUNT -ge $MAX_INTERNAL_ERRORS ]; then
                echo "❌ Maximum internal errors reached. Likely Docker image URI mismatch issue."
                echo "Please verify:"
                echo "1. The container image URI matches the newly built image"
                echo "2. The image exists in Artifact Registry"
                echo "3. Service account has proper permissions"
            fi
        fi
        break
    elif [[ "$STATUS" == "JOB_STATE_RUNNING" ]]; then
        # Reset preparation timer when job starts running
        PREP_START_TIME=$(date +%s)
        # 実行中の場合は最新のログを表示
        echo "Latest logs:"
        # Use a more portable date command
        if [[ "$(uname)" == "Darwin" ]]; then
            # macOS
            TIMESTAMP=$(date -u -v-1M '+%Y-%m-%dT%H:%M:%SZ')
        else
            # Linux
            TIMESTAMP=$(date -u -d '1 minute ago' '+%Y-%m-%dT%H:%M:%SZ')
        fi
        gcloud logging read "resource.type=ml_job AND resource.labels.job_id=$JOB_ID AND timestamp>=\"$TIMESTAMP\"" \
            --limit=5 --format="value(textPayload)" --project=$PROJECT_ID 2>/dev/null | grep -v "^$" | tail -5
    elif [[ "$STATUS" == "JOB_STATE_PENDING" ]] || [[ "$STATUS" == "JOB_STATE_QUEUED" ]] || [[ "$STATUS" == "JOB_STATE_PREPARING" ]]; then
        # Check if job is stuck in preparation
        if [ $ELAPSED_TIME -gt $MAX_PREP_TIME ]; then
            echo "⚠️  WARNING: Job has been in preparation state for over 30 minutes!"
            echo "This may indicate a Docker image URI mismatch or other configuration issue."
            echo "Consider cancelling this job and checking:"
            echo "1. Container image URI: $CONTAINER_IMAGE"
            echo "2. Image exists in Artifact Registry"
            echo "3. Service account permissions"
        fi
    fi
    
    # 30秒待機
    sleep 30
done

echo "========================================="
echo "Job monitoring completed."