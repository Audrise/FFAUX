# AudriseFFTool

Aplikasi desktop Windows untuk konversi & metadata audio berbasis FFmpeg/FFprobe
(dijalankan sebagai proses eksternal, bukan reimplementasi), dengan GUI PySide6
bergaya playlist ala foobar2000.

## Menjalankan

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

1. Unduh build FFmpeg untuk Windows (mis. dari gyan.dev atau BtbN),
   letakkan `ffmpeg.exe` dan `ffprobe.exe` di folder `bin/`, atau atur
   path-nya lewat menu **Edit > Pengaturan...** di aplikasi.
2. Jalankan aplikasi:

```bash
python main.py
```

## Menjalankan test backend (tanpa GUI)

```bash
pip install pytest
pytest tests/ -v
```

Semua modul di `core/` (kecuali `job_manager.py` dan `ffmpeg_worker.py`)
dan seluruh isi `ffmpeg/` adalah pure Python — dapat diuji tanpa
`QApplication` sama sekali.

## Struktur direktori

```
AudriseFFTool/
├── main.py                          # Entry point: wiring semua service + jalankan QApplication
├── requirements.txt                 # PySide6, pytest
│
├── gui/                              # PRESENTASI SAJA -- tidak ada logika FFmpeg di sini
│   ├── main_window.py                #   Jendela utama: menu bar, shortcut, merakit widget,
│   │                                 #   meneruskan aksi user ke JobManager/service backend
│   ├── widgets/
│   │   ├── track_table.py            #   Tabel playlist utama (drag&drop, multi-select,
│   │   │                             #   klik-kanan) -- SEKALIGUS drop area, tidak ada
│   │   │                             #   widget drop terpisah
│   │   ├── progress_panel.py         #   Progress bar agregat seluruh batch
│   │   ├── log_viewer.py             #   Panel log output FFmpeg real-time (toggle via menu View)
│   │   ├── metadata_editor.py        #   Form field metadata DINAMIS (ikut tag file terpilih) + tambah/hapus field
│   │   └── cover_art_viewer.py       #   Preview + ganti/hapus cover art, plus info resolusi & ukuran file
│   └── dialogs/
│       ├── conversion_settings_dialog.py  # Dialog Pengaturan Konversi: format output,
│       │                                  #   sample rate, bit depth, bitrate, SOXR,
│       │                                  #   compression level, custom output folder --
│       │                                  #   WAJIB muncul tiap kali Convert ditekan
│       ├── metadata_editor_dialog.py      # Dialog edit metadata (single/multi-select) + cover art + preview template
│       └── settings_dialog.py             # Dialog pengaturan aplikasi (path ffmpeg/ffprobe, dst)
│
├── core/                             # BUSINESS LOGIC -- pure Python (kecuali 2 file bertanda *)
│   ├── models/
│   │   ├── audio_file.py             #   Dataclass AudioFile: path, metadata, status,
│   │   │                             #   durasi, bitrate, sample_rate, codec, ukuran file
│   │   ├── metadata.py               #   Dataclass Metadata (tag: title/artist/album/dst)
│   │   ├── job.py                    #   Dataclass Job + enum OperationType/JobStatus
│   │   └── conversion_settings.py    #   Dataclass ConversionSettings: format output,
│   │                                 #   sample rate, bit depth, bitrate, SOXR precision,
│   │                                 #   compression level, custom output folder --
│   │                                 #   sumber kebenaran aturan "SOXR hanya FLAC/WAV"
│   ├── config_service.py             #   Load/save config aplikasi (JSON)
│   ├── filename_parser.py            #   Ekstrak metadata dari pola nama file
│   ├── template_service.py           #   Simpan/muat/terapkan template metadata
│   ├── metadata_service.py           #   Baca metadata via ffprobe, hitung default output path
│   ├── job_manager.py *              #   (butuh Qt) Antrian job + QThreadPool + agregasi sinyal
│   └── ffmpeg_worker.py *            #   (butuh Qt) QRunnable yang jalankan 1 Job di background
│
├── ffmpeg/                           # INFRASTRUKTUR -- wrapper subprocess, pure Python
│   ├── command_builder.py            #   (operasi + params dict) -> list argumen CLI FFmpeg
│   ├── ffmpeg_runner.py              #   Jalankan subprocess ffmpeg, streaming stdout per baris
│   ├── ffprobe_runner.py             #   Jalankan ffprobe, parse JSON (durasi/bitrate/codec/dst)
│   └── progress_parser.py            #   Parse output `-progress pipe:1` -> persentase 0-100
│
├── utils/
│   ├── logger.py                     #   Setup logging terpusat (console + file)
│   └── file_utils.py                 #   Validasi ekstensi audio, format durasi/ukuran/sample rate
│
├── assets/
│   ├── styles/dark.qss               #   Stylesheet dark theme ala foobar2000
│   └── templates/                    #   Template metadata default (JSON)
│
├── bin/                               # Taruh ffmpeg.exe & ffprobe.exe di sini (tidak disertakan)
├── config/                            # app_config.json & app.log (dibuat otomatis saat run)
└── tests/                             # Unit test backend (lihat daftar lengkap di bawah)
```

### Kenapa `job_manager.py` dan `ffmpeg_worker.py` ditandai `*`?

Keduanya SATU-SATUNYA file di `core/` yang boleh mengimpor PySide6 (butuh
`QObject`/sinyal untuk melaporkan progress dari thread lain ke GUI thread
secara aman). Semua modul lain di `core/` dan seluruh `ffmpeg/` sengaja
dibuat pure Python — tidak butuh `QApplication` sama sekali untuk diuji.

## Alur Convert (penting)

1. User pilih 1/beberapa/semua track di tabel (atau tidak pilih sama
   sekali → berarti semua track yang belum selesai).
2. User tekan **Convert** (`Ctrl+R`, menu File, atau klik-kanan → "Convert
   Terpilih").
3. Dialog **Pengaturan Konversi** WAJIB muncul — **satu kali saja**,
   apapun jumlah track yang dipilih (1 track atau 100 track, tetap
   sekali). Dialog ini mewakili pengaturan untuk SELURUH track yang akan
   diproses pada aksi Convert tersebut.
4. Kalau user klik Cancel di dialog, seluruh proses batal — tidak ada job
   yang dikirim ke FFmpeg sama sekali.
5. Kalau user klik Save, satu `ConversionSettings` yang sama diterapkan
   ke semua track terpilih, masing-masing jadi satu `Job` terpisah di
   `JobManager` (tetap diproses paralel per file, cuma pengaturannya yang
   dibagi bersama).

### Aturan format khusus di dialog Pengaturan Konversi

| Format Output | Bitrate | Bit Depth | SOXR + Precision | Compression Level |
|---|---|---|---|---|
| MP3 / AAC / OGG / Opus | Ya (32-320 kbps) | Tidak | Tidak (tidak ditawarkan sama sekali) | Tidak |
| **FLAC** | Tidak (bitrate FLAC variable, bukan static) | Ya | Ya, **wajib aktif** | Ya (0-12) |
| **WAV** | Tidak | Ya | Ya, **wajib aktif** | Tidak (FFmpeg tidak punya opsi ini untuk WAV) |
| ALAC | Tidak | Ya | Tidak | Tidak |

SOXR untuk FLAC/WAV bukan checkbox pilihan — dia otomatis selalu aktif
kalau formatnya FLAC atau WAV, dan baris SOXR di dialog disembunyikan
total untuk format lain (bukan cuma di-nonaktifkan).

Command FFmpeg yang dihasilkan untuk FLAC/WAV mengikuti urutan ini
(lihat `ffmpeg/command_builder.py`, dan `ConversionSettings.to_job_params()`
di `core/models/conversion_settings.py`):

```bash
# FLAC
ffmpeg -y -i <input> -map 0 -map_metadata 0 -c:v copy \
  -af aresample=resampler=soxr:precision=<precision> \
  -sample_fmt <s16/s32 sesuai bit depth> -ar <sample_rate> \
  -c:a flac -compression_level <0-12> <output.flac>

# WAV
ffmpeg -y -i <input> -map 0 -map_metadata 0 -c:v copy \
  -af aresample=resampler=soxr:precision=<precision> \
  -sample_fmt <s16/s32 sesuai bit depth> -ar <sample_rate> \
  -c:a pcm_s16le/pcm_s24le/pcm_s32le <output.wav>
```

Catatan: bit depth 24-bit dipetakan ke `-sample_fmt s32` (FLAC/FFmpeg
tidak punya sample format 24-bit murni, disimpan di container 32-bit).
Untuk WAV, `-c:a` (`pcm_s16le`/`pcm_s24le`/`pcm_s32le`) mengikuti bit
depth yang dipilih user secara konsisten dengan `-sample_fmt`-nya.

### Custom Output Folder

Dialog Pengaturan Konversi punya field folder output opsional. Kosong =
pakai `output_directory` dari Pengaturan aplikasi (atau folder sumber
file kalau itu juga kosong). Diisi = override folder itu, cuma untuk
sesi Convert yang sedang berjalan (tidak mengubah Pengaturan aplikasi).

## Alur Edit Metadata (penting)

`Ctrl+E` / menu Edit / klik-kanan → "Edit Metadata Terpilih..." membuka
**satu dialog** untuk semua track yang dipilih sekaligus (1 track atau
banyak, sama saja).

- **Field dinamis** — form menampilkan SEMUA tag yang benar-benar dibawa
  file terpilih (bukan daftar tetap), termasuk tag di luar 10 field yang
  dikenal (mis. `isrc`, `publisher`, `encoder`). Lihat
  `core/metadata_field_merger.py`.
- **Multi-select, field yang nilainya SAMA** → editable, kalau diubah
  berlaku ke SEMUA track terpilih. Ini berlaku independen per field --
  field lain yang kebetulan sama nilainya tetap bisa diedit meskipun ada
  field LAIN yang beda (mis. Album beda antar track, tapi Genre sama →
  Genre tetap bisa diedit bareng, cuma Album yang read-only).
- **Multi-select, field yang nilainya BEDA** → ditampilkan **read-only**,
  isinya gabungan semua nilai unik dipisah `" - "` (mis. `Album 1 - Album
  2`) sebagai referensi. Kalau disimpan tanpa diubah, tiap track tetap
  pakai nilai aslinya masing-masing (field ini tidak ditulis ulang sama
  sekali). Mengedit langsung field read-only ini belum didukung.
- **+ Tambah Metadata** — tombol di bawah form, menambah baris kosong
  baru (nama tag + nilai, keduanya diketik bebas oleh user). Baru jadi
  tag beneran kalau kedua kolom terisi dan dialog di-Save.
- **Hapus Metadata Terpilih** — tombol di bawah form (sebelah "+ Tambah
  Metadata"). Klik dulu field yang mau dihapus (fokus ke kolomnya, baik
  field bawaan file maupun field baru yang belum di-Save), baru klik
  tombol ini. Field bawaan yang dihapus BENAR-BENAR dibuang dari tag file
  output lewat `-metadata key=` (cara FFmpeg menghapus tag), bukan cuma
  hilang dari tampilan form.
- **Preview Template** — begitu pilih template di dropdown, isinya
  langsung ditampilkan di kotak preview di bawahnya (tanpa perlu klik
  "Terapkan Template" dulu). "Terapkan Template" tetap perlu diklik untuk
  benar-benar menimpa nilai field (cuma field yang editable yang
  ditimpa).
- **Cover art** — yang ditampilkan/diedit adalah cover milik file
  PERTAMA pada urutan terpilih. Di bawah gambar sekarang ada info
  resolusi (mis. `1400 x 1400 px`) dan ukuran file gambarnya. Cover baru
  yang dipilih sekarang **benar-benar tersimpan** saat Save (sebelumnya
  ada bug: bisa pilih gambar baru tapi hilang begitu saja saat disimpan,
  karena job `SET_COVER`-nya tidak pernah benar-benar dibuat).

### Keterbatasan yang masih ada

- Kalau field metadata DAN cover art sama-sama diubah dalam satu kali
  Save, hasilnya jadi **2 file output terpisah** (`..._tagged.ext` dan
  `..._cover.ext`), bukan 1 file gabungan — karena `JobManager` belum
  mendukung job berantai (output job A jadi input job B). Ini
  extensibility point yang sudah dicatat, belum diimplementasikan.
- Mengedit langsung field yang read-only (beda antar track) ke satu
  nilai baru yang berlaku ke semua track belum didukung secara sengaja.
  Solusinya: pakai "Hapus Metadata Terpilih" untuk buang tag itu dulu
  dari semua track, lalu pakai "+ Tambah Metadata" untuk isi ulang
  dengan nilai yang sama.

## Menambah operasi FFmpeg baru

1. Tambah entri baru di `core/models/job.py` -> `OperationType`.
2. Tambah fungsi builder di `ffmpeg/command_builder.py` dan daftarkan
   di dict `_BUILDERS` (atau panggil `register_operation()` dari luar).
3. Selesai — `JobManager` dan `FFmpegWorker` tidak perlu diubah sama sekali.

## Shortcut keyboard

| Shortcut | Aksi |
|---|---|
| `Ctrl+O` | Tambah file audio |
| `Ctrl+W` | Hapus file terpilih dari daftar |
| `Delete` | Hapus file terpilih dari daftar (alternatif) |
| `Ctrl+A` | Pilih semua baris di tabel |
| `Escape` | Batalkan seleksi (deselect semua baris) |
| `Ctrl+R` | Convert (buka dialog Pengaturan Konversi, lalu proses baris terpilih atau semua jika tidak ada seleksi) |
| `Ctrl+Shift+C` | Batalkan semua job yang berjalan |
| `Ctrl+E` | Edit metadata baris terpilih -- satu dialog untuk semua (mendukung multi-select, field dinamis, tambah/hapus tag) |
| `Ctrl+Shift+P` | Buka Pengaturan Konversi (cuma untuk pre-set default, tidak menggantikan dialog wajib saat Convert) |
| `Ctrl+,` | Buka Pengaturan aplikasi |
| `Ctrl+Q` | Keluar |

Klik kanan pada tabel juga menampilkan menu konteks dengan aksi yang
sama (Edit Metadata, Convert Terpilih, Hapus) untuk baris yang dipilih.

## Daftar test backend

| File test | Menguji |
|---|---|
| `test_command_builder.py` | Builder untuk operasi non-convert (apply_metadata + deleted_metadata_keys, extract_cover, dst) |
| `test_conversion_settings.py` | `ConversionSettings` + command FLAC/WAV/MP3 sesuai spesifikasi (SOXR, sample_fmt, compression level) |
| `test_ffmpeg_runner.py` | Eksekusi subprocess FFmpeg (mock `subprocess.Popen`) |
| `test_ffprobe_runner.py` | Parsing hasil ffprobe (`sample_rate_hz`, `bit_rate_kbps`, `codec`, `size`) |
| `test_progress_parser.py` | Parsing output `-progress pipe:1` jadi persentase |
| `test_filename_parser.py` | Ekstraksi metadata dari pola nama file |
| `test_config_service.py` | Load/save/set config aplikasi |
| `test_metadata_service.py` | Baca metadata via ffprobe (termasuk tag tak dikenal ke `extra`), ekstraksi cover art |
| `test_metadata_field_merger.py` | `build_field_views()` -- field dinamis, gabungan nilai beda, editable independen per field (termasuk skenario "beda album") |

## Status implementasi

Sudah berfungsi end-to-end:
- **Drag & drop langsung di tabel** (`track_table.py`, tidak ada widget drop terpisah)
- **Multi-select** — Edit Metadata, Convert, dan Hapus semuanya mendukung banyak baris sekaligus
- **Dialog Pengaturan Konversi wajib** setiap Convert, satu kali per aksi (bukan per track)
- **Aturan format konversi**: SOXR + sample_fmt eksklusif FLAC/WAV, bitrate cuma format lossy, compression level cuma FLAC, custom output folder opsional
- Job queue, progress real-time per baris, log viewer (toggle via menu View)
- Baca metadata otomatis saat file ditambahkan (ffprobe): title/artist/album/tahun/durasi/bitrate/sample rate/codec/ukuran file
- **Metadata editor dialog** (double-klik baris, `Ctrl+E`, atau menu konteks) — satu dialog untuk semua track terpilih sekaligus, field dinamis mengikuti tag yang benar-benar dibawa file, tambah/hapus tag, preview template, lihat bagian "Alur Edit Metadata" di atas untuk detail lengkap
- **Cover art viewer/editor** — ganti gambar dari disk (sekarang beneran tersimpan saat Save), ekstrak cover dari file audio (preview), hapus, plus info resolusi & ukuran file
- Template metadata (simpan/muat/terapkan + preview via `TemplateService`)
- Config service + dialog pengaturan aplikasi
- Menu bar penuh (File/Edit/View/Help), shortcut Ctrl, menu konteks klik-kanan, dark theme ala foobar2000

Catatan desain yang sengaja disederhanakan:
- **Mengedit field read-only (beda antar track) langsung ke satu nilai
  baru untuk semua track** belum didukung -- field itu sengaja dibuat
  read-only supaya tidak ada perubahan tidak sengaja yang menimpa nilai
  berbeda-beda tiap track. Solusinya: hapus dulu tag itu lewat "Hapus
  Metadata Terpilih" di semua track, baru isi ulang dengan nilai sama
  lewat "+ Tambah Metadata".
- Job `APPLY_METADATA` dan `SET_COVER` belum di-chain otomatis (output
  job A otomatis jadi input job B) -- kalau metadata DAN cover art
  sama-sama diubah, hasilnya jadi 2 file output terpisah, bukan 1 file
  gabungan. Extensibility point untuk `JobManager` ke depan (job dengan
  dependency/prasyarat).
- Ekstraksi cover art untuk preview berjalan sinkron (blocking sesaat),
  bukan lewat JobManager, karena operasi ringan satu file untuk pratinjau
  UI, bukan bagian dari batch.
- `TrackTable` menyimpan `audio_file_id` sebagai `Qt.ItemDataRole.UserRole`
  pada tiap baris (bukan mengandalkan index posisi statis), sehingga
  index tetap benar walau baris dihapus/diurutkan ulang.
- ALAC (lossless, tapi bukan FLAC/WAV) belum diberi perlakuan
  SOXR/sample_fmt khusus karena di luar cakupan spesifikasi yang
  diberikan — saat ini encode biasa tanpa bitrate maupun SOXR.

Belum diimplementasikan: filename parser belum disambungkan ke tombol
di UI (service-nya sudah ada & teruji di `core/filename_parser.py`),
dan penerapan filename parser sebagai sumber metadata otomatis saat
file ditambahkan ke batch.
