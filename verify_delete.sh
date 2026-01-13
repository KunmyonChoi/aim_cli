#!/bin/bash
set -e

# Setup
rm -rf test_storage
mkdir -p test_storage/v1
mkdir -p test_storage/v2
echo "v1" > test_storage/v1/data.txt
echo "v2" > test_storage/v2/data.txt

echo "1. Create Repo"
python3 -m aim_cli.main repo create delete-test-repo --type local --path $(pwd)/test_storage

echo "2. Push Versions"
python3 -m aim_cli.main model push delete-test-repo test-model ./test_storage/v1 --tag v1
python3 -m aim_cli.main model push delete-test-repo test-model ./test_storage/v2 --tag v2

echo "3. List Before Delete"
python3 -m aim_cli.main versions delete-test-repo test-model

echo "4. Delete Version v1"
python3 -m aim_cli.main model delete-version delete-test-repo test-model --tag v1 --force

echo "5. Verify Version Deletion"
if python3 -m aim_cli.main versions delete-test-repo test-model | grep -q "v1"; then
    echo "FAILURE: v1 still exists"
    exit 1
else
    echo "SUCCESS: v1 deleted"
fi

echo "6. Delete Model"
python3 -m aim_cli.main model delete delete-test-repo test-model --force

echo "7. Verify Model Deletion"
if python3 -m aim_cli.main model list delete-test-repo | grep -q "test-model"; then
    echo "FAILURE: test-model still exists"
    exit 1
else
    echo "SUCCESS: test-model deleted"
fi

# Cleanup
python3 -m aim_cli.main repo delete delete-test-repo
rm -rf test_storage
echo "All tests passed!"
