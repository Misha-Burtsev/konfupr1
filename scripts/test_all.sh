# пример: scripts/test_vfs_min.sh
#!/usr/bin/env bash
python3 "$(dirname "$0")/../main.py" --vfs "$(dirname "$0")/../vfs_src/vfs_deep.zip" --script "$(dirname "$0")/start_all.txt"
