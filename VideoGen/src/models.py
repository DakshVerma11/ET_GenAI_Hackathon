from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MarketRow:
    name: str
    close: Optional[float]
    change: Optional[float]
    trend: str
    source: str = "unknown"


@dataclass
class MarketSnapshot:
    indices: List[MarketRow] = field(default_factory=list)
    sectors_all: List[MarketRow] = field(default_factory=list)
    sectors_top_gainers: List[MarketRow] = field(default_factory=list)
    sectors_top_losers: List[MarketRow] = field(default_factory=list)
    fii_dii: Dict[str, Optional[float]] = field(default_factory=lambda: {
        "fii_net": None,
        "dii_net": None,
    })
    ipo_list: List[Dict[str, str]] = field(default_factory=list)
    skipped_symbols: List[str] = field(default_factory=list)
    provider_health: Dict[str, str] = field(default_factory=dict)


@dataclass
class SceneSpec:
    scene_number: int
    title: str
    visual: str
    on_screen_text: List[str]
    voiceover: str
    captions: List[str]
    data_used: List[str]


@dataclass
class PipelineResult:
    ok: bool
    video_path: Optional[str]
    metadata_path: Optional[str]
    error: Optional[str] = None
