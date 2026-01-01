# Product Requirements Document (PRD): File Organizer

## 1. Introduction
The **File Organizer** is a Python-based utility designed to declutter directories by automatically organizing files into categorized subfolders based on their file types (extensions), creation dates, or other metadata.

## 2. Goals
- **Decluttering**: Quickly clean up messy downloads or desktop folders.
- **Automation**: Save user time by automating manual file moving tasks.
- **Safety**: Ensure no files are lost or overwritten during the process.

## 3. User Stories
- **US1**: As a user, I want to run the tool on a specific directory so that all files inside are sorted.
- **US2**: As a user, I want files to be grouped by category (e.g., Images, Documents, Videos) so I can find them easily.
- **US3**: As a user, I want to see a log of what files were moved so I can verify the actions.
- **US4**: As a user, I want to handle duplicate filenames gracefully (e.g., rename or skip) to avoid data loss.
- **US5**: As a user, I want to be able to undo the last operation in case I organized the wrong folder.

## 4. Functional Requirements
### 4.1 Core Features
- **Categorization**: Map file extensions to categories.
  - *Images*: .jpg, .png, .gif, .svg, etc.
  - *Documents*: .pdf, .docx, .txt, .xlsx, etc.
  - *Audio*: .mp3, .wav, .flac, etc.
  - *Video*: .mp4, .mkv, .mov, etc.
  - *Archives*: .zip, .rar, .tar, etc.
  - *Scripts/Code*: .py, .js, .html, .css, etc.
  - *Others*: Fallback for unknown extensions.
- **Directory Scanning**: Recursively or non-recursively scan the target directory.
- **File Moving**: Move files to `{Target Directory}/{Category}/`.
- **Conflict Resolution**: If a file with the same name exists, append a timestamp or counter (e.g., `file_1.txt`).

### 4.2 CLI Interface
- Arguments:
  - `path`: The directory to organize (default: current directory).
  - `--undo`: Revert the last organization (optional feature).
  - `--dry-run`: Simulate the organization without moving files.

## 5. Non-Functional Requirements
- **Performance**: Should handle hundreds of files in seconds.
- **Reliability**: Must handle permission errors or read-only files gracefully.
- **Portability**: Should run on Windows, macOS, and Linux (Python cross-platform).

## 6. Technical Stack
- **Language**: Python 3.x
- **Libraries**: `os`, `shutil`, `pathlib` (Standard Library).
- **Logging**: Built-in `logging` module.
