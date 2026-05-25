import re
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ERROR_LOG = Path("workspace/memory/error.log")

# Free-tier asset constraints
FREE_TIER_MAX_PLOTS = 2
FREE_TIER_MAX_INDICATOR_DECLARATIONS = 1

# Runtime guardrails to reduce resource-exhaustion risk on hostile payloads
MAX_SCRIPT_CHARS = 200_000
MAX_SCRIPT_LINES = 5_000

# ---------------------------------------------------------------------------
# Pine Script v6 — official built-in function dictionary
# Any function call not in this set is treated as an invented/hallucinated name.
# ---------------------------------------------------------------------------
PINE_V6_BUILTINS: set[str] = {
    # declarations
    "indicator", "strategy", "library",
    # plotting
    "plot", "plotshape", "plotchar", "plotarrow", "plotbar", "plotcandle",
    "hline", "fill", "bgcolor", "barcolor",
    # alerts
    "alertcondition", "alert",
    # input
    "input", "input.bool", "input.color", "input.float", "input.int",
    "input.price", "input.session", "input.source", "input.string",
    "input.symbol", "input.text_area", "input.time", "input.timeframe",
    # ta.*
    "ta.sma", "ta.ema", "ta.wma", "ta.vwma", "ta.dema", "ta.tema", "ta.hma",
    "ta.alma", "ta.swma", "ta.linreg", "ta.rsi", "ta.mfi", "ta.cci", "ta.cmo",
    "ta.mom", "ta.roc", "ta.wpr", "ta.stoch", "ta.macd", "ta.dmi", "ta.adx",
    "ta.atr", "ta.tr", "ta.bb", "ta.bbw", "ta.kc", "ta.kcw", "ta.supertrend",
    "ta.obv", "ta.pvt", "ta.vwap", "ta.cum", "ta.change", "ta.crossover",
    "ta.crossunder", "ta.cross", "ta.rising", "ta.falling", "ta.highest",
    "ta.lowest", "ta.highestbars", "ta.lowestbars", "ta.barssince",
    "ta.valuewhen", "ta.pivothigh", "ta.pivotlow", "ta.stdev", "ta.variance",
    "ta.dev", "ta.median", "ta.mode", "ta.correlation", "ta.covariance",
    "ta.percentrank", "ta.percentile_linear_interpolation",
    "ta.percentile_nearest_rank",
    # math.*
    "math.abs", "math.acos", "math.asin", "math.atan", "math.avg", "math.ceil",
    "math.cos", "math.exp", "math.floor", "math.log", "math.log10", "math.max",
    "math.min", "math.pow", "math.random", "math.round", "math.round_to_mintick",
    "math.sign", "math.sin", "math.sqrt", "math.sum", "math.tan",
    "math.todegrees", "math.toradians",
    # str.*
    "str.contains", "str.endswith", "str.format", "str.format_time",
    "str.length", "str.lower", "str.match", "str.pos", "str.replace",
    "str.replace_all", "str.split", "str.startswith", "str.substring",
    "str.tostring", "str.tonumber", "str.upper",
    # array.*
    "array.new", "array.new_bool", "array.new_color", "array.new_float",
    "array.new_int", "array.new_line", "array.new_label", "array.new_string",
    "array.new_box", "array.new_table", "array.push", "array.pop",
    "array.shift", "array.unshift", "array.insert", "array.remove",
    "array.size", "array.get", "array.set", "array.first", "array.last",
    "array.clear", "array.slice", "array.copy", "array.concat", "array.join",
    "array.reverse", "array.sort", "array.sort_indices", "array.includes",
    "array.indexof", "array.lastindexof", "array.min", "array.max",
    "array.range", "array.sum", "array.avg", "array.median", "array.mode",
    "array.stdev", "array.variance", "array.covariance", "array.correlation",
    "array.percentile_linear_interpolation", "array.percentile_nearest_rank",
    "array.percentrank", "array.fill", "array.from",
    # matrix.*
    "matrix.new", "matrix.get", "matrix.set", "matrix.rows", "matrix.columns",
    "matrix.row", "matrix.col", "matrix.reshape", "matrix.transpose",
    "matrix.submatrix", "matrix.copy", "matrix.add_row", "matrix.add_col",
    "matrix.remove_row", "matrix.remove_col", "matrix.swap_rows",
    "matrix.swap_columns", "matrix.fill", "matrix.sum", "matrix.diff",
    "matrix.mult", "matrix.det", "matrix.inv", "matrix.pinv", "matrix.rank",
    "matrix.trace", "matrix.is_zero", "matrix.is_identity", "matrix.is_binary",
    "matrix.is_symmetric", "matrix.is_antisymmetric", "matrix.is_diagonal",
    "matrix.is_antidiagonal", "matrix.is_triangular", "matrix.eigenvalues",
    "matrix.eigenvectors", "matrix.kron", "matrix.pow",
    # map.*
    "map.new", "map.put", "map.get", "map.contains", "map.remove",
    "map.clear", "map.size", "map.keys", "map.values", "map.copy",
    "map.put_all",
    # color.*
    "color.new", "color.rgb", "color.r", "color.g", "color.b", "color.t",
    "color.from_gradient",
    # line.*
    "line.new", "line.set_x1", "line.set_x2", "line.set_y1", "line.set_y2",
    "line.set_xy1", "line.set_xy2", "line.set_xloc", "line.set_extend",
    "line.set_color", "line.set_style", "line.set_width", "line.get_x1",
    "line.get_x2", "line.get_y1", "line.get_y2", "line.get_price",
    "line.delete", "line.copy",
    # label.*
    "label.new", "label.set_x", "label.set_y", "label.set_xy",
    "label.set_xloc", "label.set_yloc", "label.set_text",
    "label.set_text_font_family", "label.set_color", "label.set_textcolor",
    "label.set_size", "label.set_style", "label.set_tooltip",
    "label.get_x", "label.get_y", "label.get_text", "label.delete",
    "label.copy",
    # box.*
    "box.new", "box.set_left", "box.set_right", "box.set_top", "box.set_bottom",
    "box.set_border_color", "box.set_border_style", "box.set_border_width",
    "box.set_bgcolor", "box.set_text", "box.set_text_color", "box.set_text_size",
    "box.set_text_halign", "box.set_text_valign", "box.set_text_wrap",
    "box.set_text_font_family", "box.get_left", "box.get_right", "box.get_top",
    "box.get_bottom", "box.delete", "box.copy",
    # table.*
    "table.new", "table.cell", "table.cell_set_text", "table.cell_set_text_color",
    "table.cell_set_text_size", "table.cell_set_text_halign",
    "table.cell_set_text_valign", "table.cell_set_text_font_family",
    "table.cell_set_bgcolor", "table.cell_set_width", "table.cell_set_height",
    "table.cell_set_tooltip", "table.merge_cells", "table.set_bgcolor",
    "table.set_border_color", "table.set_border_width", "table.set_frame_color",
    "table.set_frame_width", "table.set_position", "table.delete", "table.clear",
    # polyline.*
    "polyline.new", "polyline.delete",
    # request.*
    "request.security", "request.security_lower_tf", "request.dividends",
    "request.earnings", "request.splits", "request.quandl", "request.financial",
    "request.economic", "request.seed",
    # ticker.*
    "ticker.new", "ticker.modify", "ticker.heikinashi", "ticker.renko",
    "ticker.pointfigure", "ticker.kagi", "ticker.linebreak",
    # chart.*
    "chart.point.new", "chart.point.copy", "chart.point.from_index",
    "chart.point.from_time", "chart.point.now",
    # strategy.*
    "strategy.entry", "strategy.exit", "strategy.close", "strategy.close_all",
    "strategy.cancel", "strategy.cancel_all", "strategy.order",
    "strategy.risk.allow_entry_in", "strategy.risk.max_cons_loss_days",
    "strategy.risk.max_drawdown", "strategy.risk.max_intraday_filled_orders",
    "strategy.risk.max_intraday_loss", "strategy.risk.max_position_size",
    # timeframe.*
    "timeframe.change", "timeframe.in_seconds",
    # session.*
    "session.ismarket", "session.ispremarket", "session.ispostmarket",
    "session.isfirstbar", "session.islastbar", "session.isfirstbar_regular",
    "session.islastbar_regular",
    # log.* / runtime.*
    "log.error", "log.warning", "log.info", "runtime.error",
    # syminfo.* properties used as calls
    "syminfo.tickerid", "syminfo.ticker", "syminfo.prefix", "syminfo.root",
    "syminfo.currency", "syminfo.basecurrency", "syminfo.description",
    "syminfo.type", "syminfo.session", "syminfo.timezone", "syminfo.country",
    "syminfo.mintick", "syminfo.pointvalue", "syminfo.volumetype",
    # type casts / constructors
    "int", "float", "bool", "string", "color",
    "na", "nz", "fixnan",
}

# ---------------------------------------------------------------------------
# MQL5 — official standard library function dictionary
# ---------------------------------------------------------------------------
MQL5_BUILTINS: set[str] = {
    # event handlers
    "OnInit", "OnDeinit", "OnTick", "OnTimer", "OnTrade", "OnTradeTransaction",
    "OnBookEvent", "OnChartEvent", "OnStart", "OnTester", "OnTesterInit",
    "OnTesterPass", "OnTesterDeinit", "OnCalculate",
    # trade
    "OrderSend", "OrderClose", "OrderModify", "OrderDelete", "OrderSelect",
    "OrdersTotal", "OrdersHistoryTotal", "OrderGetDouble", "OrderGetInteger",
    "OrderGetString",
    # account
    "AccountInfoDouble", "AccountInfoInteger", "AccountInfoString",
    "AccountBalance", "AccountCredit", "AccountEquity", "AccountFreeMargin",
    "AccountMargin", "AccountName", "AccountNumber", "AccountProfit",
    "AccountServer", "AccountStopoutLevel", "AccountStopoutMode",
    # symbol
    "SymbolInfoDouble", "SymbolInfoInteger", "SymbolInfoString",
    "SymbolInfoTick", "SymbolSelect",
    # built-in indicators
    "iAC", "iAD", "iADX", "iADXWilder", "iAlligator", "iAMA", "iAO",
    "iATR", "iBands", "iBearsPower", "iBullsPower", "iCCI", "iChaikin",
    "iCustom", "iDEMA", "iDeMarker", "iEnvelopes", "iForce", "iFractals",
    "iFrAMA", "iGator", "iIchimoku", "iBWMFI", "iMomentum", "iMFI",
    "iMA", "iMACD", "iOBV", "iOsMA", "iRSI", "iRVI", "iSAR", "iStdDev",
    "iStochastic", "iTEMA", "iTriX", "iUltimateOscillator", "iVIDyA",
    "iVolumes", "iWPR", "iZigZag",
    # series / bars
    "CopyBuffer", "CopyRates", "CopyTime", "CopyOpen", "CopyHigh", "CopyLow",
    "CopyClose", "CopyTickVolume", "CopyRealVolume", "CopySpread",
    "ArraySetAsSeries", "ArrayGetAsSeries", "Bars", "iBars", "iBarShift",
    "iClose", "iHigh", "iHighest", "iLow", "iLowest", "iOpen", "iTime",
    "iVolume",
    # indicator setup
    "SetIndexBuffer", "SetIndexStyle", "SetIndexLabel", "SetIndexEmptyValue",
    "SetIndexShift", "SetIndexDrawBegin", "IndicatorDigits", "IndicatorShortName",
    "IndicatorSetDouble", "IndicatorSetInteger", "IndicatorSetString",
    "PlotIndexSetDouble", "PlotIndexSetInteger", "PlotIndexSetString",
    # math
    "MathAbs", "MathArccos", "MathArcsin", "MathArctan", "MathCeil",
    "MathCos", "MathExp", "MathFloor", "MathLog", "MathLog10", "MathMax",
    "MathMin", "MathMod", "MathPow", "MathRand", "MathRound", "MathSin",
    "MathSqrt", "MathSrand", "MathTan", "MathIsValidNumber",
    # string
    "StringAdd", "StringBufferLen", "StringCompare", "StringConcatenate",
    "StringFill", "StringFind", "StringFormat", "StringGetCharacter",
    "StringInit", "StringLen", "StringLower", "StringReplace",
    "StringSetCharacter", "StringSplit", "StringSubstr", "StringToDouble",
    "StringToInteger", "StringToLower", "StringToTime", "StringToUpper",
    "StringTrimLeft", "StringTrimRight", "StringUpper", "IntegerToString",
    "DoubleToString", "TimeToString", "NormalizeDouble",
    # array
    "ArrayBsearch", "ArrayCopy", "ArrayFill", "ArrayFree", "ArrayInitialize",
    "ArrayIsDynamic", "ArrayIsSeries", "ArrayMaximum", "ArrayMinimum",
    "ArrayPrint", "ArrayRange", "ArrayResize", "ArrayReverse", "ArraySize",
    "ArraySort",
    # time
    "TimeCurrent", "TimeGMT", "TimeLocal", "TimeTradeServer", "TimeToStruct",
    "StructToTime", "TimeToString", "TimeDaylightSavings", "TimeGMTOffset",
    # chart / objects
    "ChartApplyTemplate", "ChartClose", "ChartFirst", "ChartGetDouble",
    "ChartGetInteger", "ChartGetString", "ChartID", "ChartIndicatorAdd",
    "ChartIndicatorDelete", "ChartIndicatorGet", "ChartIndicatorName",
    "ChartIndicatorsTotal", "ChartNavigate", "ChartNext", "ChartOpen",
    "ChartPeriodChange", "ChartPrint", "ChartRedraw", "ChartSaveTemplate",
    "ChartScreenShot", "ChartSetDouble", "ChartSetInteger", "ChartSetString",
    "ChartSetSymbolPeriod", "ChartWindowFind",
    "ObjectCreate", "ObjectDelete", "ObjectFind", "ObjectGetDouble",
    "ObjectGetInteger", "ObjectGetString", "ObjectGetTimeByValue",
    "ObjectGetValueByTime", "ObjectMove", "ObjectName", "ObjectsDeleteAll",
    "ObjectSetDouble", "ObjectSetInteger", "ObjectSetString", "ObjectsTotal",
    # output / notifications
    "Print", "Alert", "Comment", "PlaySound", "SendFTP", "SendMail",
    "SendNotification", "printf",
    # file I/O
    "FileClose", "FileCopy", "FileDelete", "FileFlush", "FileGetInteger",
    "FileIsEnding", "FileIsExist", "FileIsLineEnding", "FileMove", "FileOpen",
    "FileReadArray", "FileReadBool", "FileReadDatetime", "FileReadDouble",
    "FileReadFloat", "FileReadInteger", "FileReadLong", "FileReadNumber",
    "FileReadString", "FileReadStruct", "FileSeek", "FileSize", "FileTell",
    "FileWrite", "FileWriteArray", "FileWriteDouble", "FileWriteFloat",
    "FileWriteInteger", "FileWriteLong", "FileWriteString", "FileWriteStruct",
    # misc
    "GetLastError", "ResetLastError", "GetTickCount", "Sleep", "IsConnected",
    "IsDemo", "IsDllsAllowed", "IsExpertEnabled", "IsLibrariesAllowed",
    "IsOptimization", "IsStopped", "IsTesting", "IsTradeAllowed",
    "IsTradeContextBusy", "IsVisualMode", "UninitializeReason",
    "TerminalInfoDouble", "TerminalInfoInteger", "TerminalInfoString",
    "MarketInfo", "Period", "Symbol", "Digits", "Point",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _log_violation(context: str, error_code: str, detail: str) -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "error_code": error_code,
        "detail": detail,
    }
    with ERROR_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _strip_comments(code: str, lang: Literal["pine", "mql5"]) -> str:
    """Remove single-line and block comments so they don't pollute scans."""
    if lang == "pine":
        # Pine uses // for line comments only
        code = re.sub(r"//[^\n]*", "", code)
    else:
        # MQL5 uses // and /* ... */
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        code = re.sub(r"//[^\n]*", "", code)
    return code


def _extract_call_names(code: str) -> list[str]:
    """
    Return every identifier that precedes an opening parenthesis.
    Captures both simple names (foo) and namespaced names (ns.foo or ns.ns.foo).
    """
    pattern = r"((?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*)\s*\("
    return re.findall(pattern, code)


def _alert_conditions_are_grouped(lines: list[str]) -> bool:
    """
    Alert conditions must form a contiguous block — only blank lines or
    comment lines may appear between them. Returns True if the constraint holds.
    """
    alert_indices = [
        i for i, ln in enumerate(lines) if re.search(r"\balertcondition\s*\(", ln)
    ]
    if len(alert_indices) <= 1:
        return True

    first, last = alert_indices[0], alert_indices[-1]
    for i in range(first, last + 1):
        stripped = lines[i].strip()
        is_blank = stripped == ""
        is_comment = stripped.startswith("//")
        is_alert = re.search(r"\balertcondition\s*\(", lines[i]) is not None
        if not (is_blank or is_comment or is_alert):
            return False
    return True


# ---------------------------------------------------------------------------
# Public validation gates
# ---------------------------------------------------------------------------

def _enforce_script_size_guards(code: str, context: str, lang: Literal["pine", "mql5"]) -> None:
    char_count = len(code)
    line_count = len(code.splitlines())
    if char_count > MAX_SCRIPT_CHARS:
        detail = f"Script size {char_count} chars exceeds max {MAX_SCRIPT_CHARS}."
        _log_violation(context, f"{lang.upper()}_SCRIPT_TOO_LARGE", detail)
        print(f"[SANDBOX] {detail} File save blocked.", file=sys.stderr)
        sys.exit(1)
    if line_count > MAX_SCRIPT_LINES:
        detail = f"Script size {line_count} lines exceeds max {MAX_SCRIPT_LINES}."
        _log_violation(context, f"{lang.upper()}_SCRIPT_TOO_MANY_LINES", detail)
        print(f"[SANDBOX] {detail} File save blocked.", file=sys.stderr)
        sys.exit(1)


def validate_pine_v6(code: str, output_path: str | None = None) -> None:
    """
    Intercepts a Pine Script v6 generation sequence before disk write.
    Kills the process on any violation and logs to error.log.
    """
    context = output_path or "<pine_buffer>"
    _enforce_script_size_guards(code, context, "pine")
    clean = _strip_comments(code, "pine")
    lines = code.splitlines()

    # 1. Indicator declaration count
    decl_count = len(re.findall(r"\bindicator\s*\(", clean))
    if decl_count > FREE_TIER_MAX_INDICATOR_DECLARATIONS:
        detail = f"Found {decl_count} indicator() declarations; max is {FREE_TIER_MAX_INDICATOR_DECLARATIONS}."
        _log_violation(context, "PINE_EXCESS_INDICATORS", detail)
        print(f"[SANDBOX] {detail} File save blocked.", file=sys.stderr)
        sys.exit(1)

    # 2. plot() series count — free-tier ceiling
    plot_count = len(re.findall(r"\bplot\s*\(", clean))
    if plot_count > FREE_TIER_MAX_PLOTS:
        detail = f"Found {plot_count} plot() calls; free-tier max is {FREE_TIER_MAX_PLOTS}."
        _log_violation(context, "PINE_EXCESS_PLOTS", detail)
        print(f"[SANDBOX] {detail} File save blocked.", file=sys.stderr)
        sys.exit(1)

    # 3. Alert condition grouping
    if not _alert_conditions_are_grouped(lines):
        detail = "alertcondition() calls are not grouped into a contiguous block."
        _log_violation(context, "PINE_UNGROUPED_ALERTS", detail)
        print(f"[SANDBOX] {detail} File save blocked.", file=sys.stderr)
        sys.exit(1)

    # 4. Function name whitelist scan
    calls = _extract_call_names(clean)
    for name in calls:
        # Skip user-defined identifiers (lowercase, no namespace dot) — only flag
        # calls that LOOK like they're invoking a known namespace but use a bad method.
        has_namespace = "." in name
        if has_namespace and name not in PINE_V6_BUILTINS:
            detail = f"Unrecognized Pine Script v6 function: '{name}'."
            _log_violation(context, "PINE_UNKNOWN_FUNCTION", detail)
            print(f"[SANDBOX] {detail} File save blocked.", file=sys.stderr)
            sys.exit(1)


def validate_mql5(code: str, output_path: str | None = None) -> None:
    """
    Intercepts an MQL5 generation sequence before disk write.
    Kills the process on any violation and logs to error.log.
    """
    context = output_path or "<mql5_buffer>"
    _enforce_script_size_guards(code, context, "mql5")
    clean = _strip_comments(code, "mql5")

    # 1. Indicator buffer count — free-tier ceiling
    buffer_match = re.search(r"#property\s+indicator_buffers\s+(\d+)", clean)
    if buffer_match:
        buf_count = int(buffer_match.group(1))
        if buf_count > FREE_TIER_MAX_PLOTS:
            detail = f"indicator_buffers={buf_count}; free-tier max is {FREE_TIER_MAX_PLOTS}."
            _log_violation(context, "MQL5_EXCESS_BUFFERS", detail)
            print(f"[SANDBOX] {detail} File save blocked.", file=sys.stderr)
            sys.exit(1)

    # 2. Function name whitelist scan (capitalized calls only — MQL5 convention)
    calls = _extract_call_names(clean)
    for name in calls:
        # Only check calls that start with a capital letter (library functions).
        # User-defined functions conventionally start lower-case or are in scope.
        if name[0].isupper() and name not in MQL5_BUILTINS:
            detail = f"Unrecognized MQL5 standard library function: '{name}'."
            _log_violation(context, "MQL5_UNKNOWN_FUNCTION", detail)
            print(f"[SANDBOX] {detail} File save blocked.", file=sys.stderr)
            sys.exit(1)


def gate(code: str, lang: Literal["pine", "mql5"], output_path: str | None = None) -> None:
    """Unified entry point. Call this before any code is committed to disk."""
    if lang == "pine":
        validate_pine_v6(code, output_path)
    elif lang == "mql5":
        validate_mql5(code, output_path)
    else:
        raise ValueError(f"Unsupported language: {lang!r}. Expected 'pine' or 'mql5'.")
