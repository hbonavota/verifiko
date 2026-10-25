from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.analysis_trace import AnalysisTrace


class AnalysisTraceBuilder:
    @staticmethod
    def build(
        signals: list[AnalysisSignal],
        layers_executed: tuple[str, ...] | list[str],
    ) -> AnalysisTrace:
        grouped: dict[str, list[AnalysisSignal]] = {}
        for signal in signals:
            grouped.setdefault(signal.source, []).append(signal)

        return AnalysisTrace(
            layers_executed=tuple(layers_executed),
            signals_by_source={
                source: tuple(items) for source, items in grouped.items()
            },
            total_signals=len(signals),
        )

    @staticmethod
    def from_signals(signals: list[AnalysisSignal]) -> AnalysisTrace:
        seen_sources: list[str] = []
        grouped: dict[str, list[AnalysisSignal]] = {}
        for signal in signals:
            if signal.source not in grouped:
                grouped[signal.source] = []
                seen_sources.append(signal.source)
            grouped[signal.source].append(signal)

        return AnalysisTrace(
            layers_executed=tuple(seen_sources),
            signals_by_source={
                source: tuple(items) for source, items in grouped.items()
            },
            total_signals=len(signals),
        )
