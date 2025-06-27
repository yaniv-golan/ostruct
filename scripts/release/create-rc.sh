#!/bin/bash
# scripts/release/create-rc.sh
# Script to create release candidate tags for ostruct

set -e  # Exit on any error

VERSION=$1
RC_NUMBER=$2

if [[ -z "$VERSION" || -z "$RC_NUMBER" ]]; then
    echo "Usage: $0 <version> <rc_number>"
    echo "Example: $0 1.0.0 1"
    echo ""
    echo "This script creates a signed release candidate tag and pushes it to origin."
    echo "The tag format will be: v<version>-rc<rc_number>"
    echo ""
    echo "Current branch: $(git branch --show-current)"
    echo "Latest commit: $(git log --oneline -1)"
    exit 1
fi

# Validate we're on a release branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ ! "$CURRENT_BRANCH" =~ ^release/ ]]; then
    echo "❌ Error: Must be on a release branch (release/*)"
    echo "Current branch: $CURRENT_BRANCH"
    echo "Switch to the release branch first: git checkout release/v$VERSION"
    exit 1
fi

# Validate version format (basic check)
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ Error: Version must be in format X.Y.Z (e.g., 1.0.0)"
    echo "Provided: $VERSION"
    exit 1
fi

# Validate RC number is a positive integer
if [[ ! "$RC_NUMBER" =~ ^[0-9]+$ ]]; then
    echo "❌ Error: RC number must be a positive integer"
    echo "Provided: $RC_NUMBER"
    exit 1
fi

TAG_NAME="v${VERSION}-rc${RC_NUMBER}"

# Check if tag already exists
if git tag -l | grep -q "^${TAG_NAME}$"; then
    echo "❌ Error: Tag $TAG_NAME already exists"
    echo "Existing tags:"
    git tag -l | grep -E "^v${VERSION}-rc[0-9]+$" | sort -V
    exit 1
fi

# Show what we're about to do
echo "🏷️  Creating release candidate tag:"
echo "   Tag: $TAG_NAME"
echo "   Branch: $CURRENT_BRANCH"
echo "   Commit: $(git log --oneline -1)"
echo ""

# Confirm with user
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted by user"
    exit 1
fi

# Create signed tag
echo "📝 Creating signed tag $TAG_NAME..."
git tag -s "$TAG_NAME" -m "Release candidate $RC_NUMBER for version $VERSION

This is a pre-release version for testing purposes.
- Built from branch: $CURRENT_BRANCH
- Commit: $(git rev-parse HEAD)
- Created: $(date -u '+%Y-%m-%d %H:%M:%S UTC')

For testing installation:
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ostruct-cli==${VERSION}rc${RC_NUMBER}
"

# Push tag to origin
echo "🚀 Pushing tag to origin..."
git push origin "$TAG_NAME"

echo ""
echo "✅ Release candidate $TAG_NAME created and pushed successfully!"
echo ""
echo "🔗 GitHub Actions should now be building and publishing to TestPyPI:"
echo "   https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\([^.]*\).*/\1/')/actions"
echo ""
echo "📦 Once published, test installation with:"
echo "   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ostruct-cli==${VERSION}rc${RC_NUMBER}"
echo ""
echo "🏷️  All RC tags for this version:"
git tag -l | grep -E "^v${VERSION}-rc[0-9]+$" | sort -V || echo "   (none yet)"
