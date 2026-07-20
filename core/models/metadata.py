"""Model data untuk metadata audio.

Modul ini murni Python (tidak ada dependensi Qt) sehingga bisa diuji
langsung dengan pytest tanpa perlu QApplication.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Metadata:
    """Representasi tag metadata satu file audio.

    Field yang bernilai None berarti "tidak diketahui / tidak diubah",
    bukan string kosong. Ini penting agar operasi "apply template" tidak
    menimpa tag yang sudah ada dengan nilai kosong secara tidak sengaja.
    """

    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    album_artist: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[str] = None
    track_number: Optional[str] = None
    disc_number: Optional[str] = None
    url: Optional[str] = None
    comment: Optional[str] = None
    composer: Optional[str] = None
    cover_art_path: Optional[str] = None

    extra: dict = field(default_factory=dict)
    """Tag tambahan yang tidak punya field khusus (mis. ISRC, publisher)."""

    def to_dict(self, include_none: bool = False) -> dict:
        data = asdict(self)
        extra = data.pop("extra")
        if not include_none:
            data = {k: v for k, v in data.items() if v is not None}
        data.update(extra)
        return data

    def merge(self, other: "Metadata") -> "Metadata":
        merged = Metadata.from_dict(self.to_dict(include_none=True))

        known_fields = set(Metadata.__dataclass_fields__) - {"extra"}

        for key, value in other.to_dict(include_none=True).items():
            if value is None:
                continue

            if key in known_fields:
                setattr(merged, key, value)
            else:
                merged.extra[key] = value

        return merged

    @classmethod
    def from_dict(cls, data: dict) -> "Metadata":
        known_fields = {f for f in cls.__dataclass_fields__ if f != "extra"}
        base = {k: v for k, v in data.items() if k in known_fields}
        extra = {k: v for k, v in data.items() if k not in known_fields}
        return cls(**base, extra=extra)
