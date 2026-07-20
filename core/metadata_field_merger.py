"""Utilitas murni Python untuk membangun daftar field form "Edit Metadata".

Modul ini sengaja tidak punya dependensi Qt sama sekali (murni dataclass +
dict) supaya logikanya bisa diuji langsung dengan pytest, konsisten dengan
core/models/metadata.py.

Aturan penggabungan field untuk multi-select (lihat juga
gui/widgets/metadata_editor.py):

- Field yang ditampilkan di form = gabungan (union) seluruh tag yang
  benar-benar dimiliki file-file terpilih -- bukan daftar field tetap.
  Kalau sebuah lagu punya 20 tag, ke-20 tag itu yang tampil.
- Field "dikenal" (title, artist, album, dst) selalu tampil lebih dulu
  sesuai urutan tetap supaya form tidak acak; field ekstra (mis. isrc,
  publisher, encoder) menyusul sesuai urutan kemunculannya.
- Kalau nilai field SAMA di semua file terpilih (termasuk saat cuma 1
  file terpilih), field itu bisa diedit seperti biasa.
- Kalau nilainya BERBEDA antar file, field ditampilkan read-only berisi
  semua nilai unik tsb digabung dengan " - ". Field read-only ini tidak
  didukung untuk diedit sekaligus ke semua track (belum diimplementasikan
  secara sengaja) -- kalau disimpan tanpa diubah, field itu diabaikan per
  track sehingga nilai asli masing-masing track tetap dipertahankan.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.models.audio_file import AudioFile

# Field standar yang sudah dikenal Metadata, dengan label Indonesia serta
# urutan tampil tetap.
KNOWN_FIELD_LABELS: dict[str, str] = {
    "title": "Judul",
    "artist": "Artis",
    "album": "Album",
    "album_artist": "Artis Album",
    "genre": "Genre",
    "year": "Tahun",
    "track_number": "Nomor Trek",
    "disc_number": "Nomor Disc",
    "composer": "Komposer",
    "url": "URL",
    "comment": "Komentar",
}
_KNOWN_FIELD_ORDER = list(KNOWN_FIELD_LABELS.keys())

# Nilai gabungan antar track/album yang berbeda dipisah dengan ini.
VALUE_SEPARATOR = " - "


def field_label(field_key: str) -> str:
    """Label tampilan untuk sebuah field.

    Field dikenal pakai label Indonesia dari KNOWN_FIELD_LABELS. Field
    ekstra/tidak dikenal (tag tambahan seperti isrc, publisher) dipakai
    apa adanya dengan huruf awal tiap kata dikapitalkan.
    """
    if field_key in KNOWN_FIELD_LABELS:
        return KNOWN_FIELD_LABELS[field_key]
    return field_key.replace("_", " ").strip().title()


@dataclass
class FieldView:
    """Satu baris field pada form Edit Metadata."""

    key: str
    label: str
    value: str
    editable: bool  # False kalau nilainya beda antar track terpilih


def build_field_views(audio_files: list[AudioFile]) -> list[FieldView]:
    """Bangun daftar FieldView untuk satu atau banyak AudioFile terpilih."""
    if not audio_files:
        return []

    per_file_dicts = [af.metadata.to_dict() for af in audio_files]

    ordered_keys: list[str] = []
    seen_keys: set[str] = set()

    for key in _KNOWN_FIELD_ORDER:
        if any(key in d for d in per_file_dicts):
            ordered_keys.append(key)
            seen_keys.add(key)

    for d in per_file_dicts:
        for key in d:
            if key == "cover_art_path" or key in seen_keys:
                continue
            ordered_keys.append(key)
            seen_keys.add(key)

    views: list[FieldView] = []
    for key in ordered_keys:
        values = [str(d.get(key, "") or "") for d in per_file_dicts]
        distinct_values = list(dict.fromkeys(values))  # unik, urutan kemunculan pertama
        if len(distinct_values) <= 1:
            views.append(
                FieldView(
                    key=key,
                    label=field_label(key),
                    value=distinct_values[0] if distinct_values else "",
                    editable=True,
                )
            )
        else:
            views.append(
                FieldView(
                    key=key,
                    label=field_label(key),
                    value=VALUE_SEPARATOR.join(distinct_values),
                    editable=False,
                )
            )
    return views
