#!/bin/bash

# CoE-RagPipeline 실행 스크립트
# .venv 가상환경을 활성화하고 .env 설정으로 서버를 실행합니다.

set -e  # 에러 발생 시 스크립트 중단

VENV_DIR="./.venv"
ENV_FILE="./.env"

echo "🚀 CoE-RagPipeline 서버 시작 중..."

# .env 파일 존재 확인
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env 파일이 존재하지 않습니다."
    echo "📝 .env.example 파일을 복사하여 .env 파일을 생성하세요:"
    echo "   cp .env.example .env"
    echo "   nano .env  # 또는 원하는 에디터로 편집"
    echo ""
    echo "🔧 필수 설정 항목:"
    echo "   - SKAX_API_KEY: ax4 모델 사용을 위한 API 키"
    echo "   - OPENAI_API_KEY: OpenAI 서비스 사용을 위한 API 키"
    echo "   - JWT_SECRET_KEY: JWT 토큰 암호화를 위한 비밀키"
    exit 1
fi

# 가상환경 존재 확인 및 생성
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 가상환경이 존재하지 않습니다. 새로 생성합니다..."
    python3.11 -m venv "$VENV_DIR"
    echo "✅ 가상환경 생성 완료"
fi

# 가상환경 활성화
echo "🔄 가상환경 활성화 중..."
source "$VENV_DIR/bin/activate"

# 의존성 설치/업데이트
# .installed 마커 파일이 없거나 requirements.txt가 변경되었을 경우에만 설치를 진행합니다.
REQUIREMENTS_FILE="requirements.txt"
INSTALLED_MARKER="$VENV_DIR/.installed"

# requirements.txt의 해시값을 저장할 파일
REQUIREMENTS_HASH_FILE="$VENV_DIR/.requirements_hash"

# 오프라인용 휠 디렉터리 탐지
WHEEL_DIR="${WHEEL_DIR:-./vendor/wheels}"
PIP_ARGS=()
HAS_LOCAL_WHEELS=false
if [ -d "$WHEEL_DIR" ] && ls "$WHEEL_DIR"/*.whl >/dev/null 2>&1; then
    echo "📦 오프라인 휠 디렉터리 감지: $WHEEL_DIR"
    PIP_ARGS+=(--no-index "--find-links=$WHEEL_DIR")
    HAS_LOCAL_WHEELS=true
fi

# 현재 requirements.txt의 해시값 계산 (shasum 미존재 환경 대비)
CURRENT_HASH=$(python3 - <<'PY' "$REQUIREMENTS_FILE"
import hashlib, pathlib, sys
path = pathlib.Path(sys.argv[1])
if not path.exists():
    print("")
else:
    print(hashlib.sha256(path.read_bytes()).hexdigest())
PY
)

# 이전 해시값 읽기
PREVIOUS_HASH=""
if [ -f "$REQUIREMENTS_HASH_FILE" ]; then
    PREVIOUS_HASH=$(cat "$REQUIREMENTS_HASH_FILE")
fi

if [ ! -f "$INSTALLED_MARKER" ] || [ "$CURRENT_HASH" != "$PREVIOUS_HASH" ]; then
    echo "📚 의존성 설치/업데이트 중..."
    echo "🛠️  pip/setuptools/wheel 부트스트랩 중..."
    python -m ensurepip --upgrade >/dev/null 2>&1 || python -m ensurepip --upgrade
    BOOTSTRAP_PKGS=(pip setuptools wheel)
    INSTALL_PKGS=()
    if [ "$HAS_LOCAL_WHEELS" = true ]; then
        for pkg in "${BOOTSTRAP_PKGS[@]}"; do
            if ! PKG="$pkg" python - <<'PY' >/dev/null 2>&1; then
import importlib, os, sys
sys.exit(0 if importlib.util.find_spec(os.environ["PKG"]) else 1)
PY
                if ! ls "$WHEEL_DIR"/"$pkg"-*.whl >/dev/null 2>&1; then
                    echo "❌ ${pkg} 휠을 찾을 수 없습니다: $WHEEL_DIR/${pkg}-*.whl"
                    echo "   외부망에서 'python -m pip download ${pkg} -d $WHEEL_DIR' 후 다시 실행하세요."
                    exit 1
                fi
                INSTALL_PKGS+=("$pkg")
            fi
        done
    else
        INSTALL_PKGS=("${BOOTSTRAP_PKGS[@]}")
    fi
    if [ "${#INSTALL_PKGS[@]}" -gt 0 ]; then
        python -m pip install "${PIP_ARGS[@]}" --upgrade "${INSTALL_PKGS[@]}"
    fi
    if ! python -m uv --version >/dev/null 2>&1; then
        echo "🧰 uv 설치 중..."
        if [ "$HAS_LOCAL_WHEELS" = true ] && ! ls "$WHEEL_DIR"/uv-*.whl >/dev/null 2>&1; then
            echo "❌ uv 휠을 찾을 수 없습니다. 외부망에서 'python -m pip download uv -d $WHEEL_DIR' 실행 후 다시 시도하세요."
            exit 1
        fi
        pip install "${PIP_ARGS[@]}" uv
    fi
    HNSWLIB_NO_NATIVE=1 uv pip install --no-build-isolation "${PIP_ARGS[@]}" -r "$REQUIREMENTS_FILE"
    
    # 설치 완료 후 마커 파일 생성 및 해시값 저장
    touch "$INSTALLED_MARKER"
    echo "$CURRENT_HASH" > "$REQUIREMENTS_HASH_FILE"
    echo "✅ 의존성 설치/업데이트 완료"
elif [ -f "$INSTALLED_MARKER" ]; then
    echo "✅ 의존성 이미 설치됨 (requirements.txt 변경 없음)"
fi

# .env 파일 로드 및 서버 실행
echo "🌍 환경변수 로드: .env"
echo "🎯 서버 실행 중... (http://localhost:8001)"
echo "⏹️  서버 중지: Ctrl+C"
echo ""

# 환경변수 파일을 지정하여 Python 실행
export $(grep -v '^#' "$ENV_FILE" | xargs)
python main.py
