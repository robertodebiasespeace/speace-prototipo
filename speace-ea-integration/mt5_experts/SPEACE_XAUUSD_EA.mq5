//+------------------------------------------------------------------+
//|                                      SPEACE_XAUUSD_EA.mq5         |
//|                                              SPEACE Autonomous EA |
//|                              Roberto De Biase / SPEACE Cortex     |
//+------------------------------------------------------------------+
#property copyright   "SPEACE XAUUSD Expert Advisor v1.0"
#property link        "https://speace.ai"
#property version     "1.00"
#property strict

//+------------------------------------------------------------------+
//| PARAMETERS (synchronized with speace_ea_params.json)              |
//+------------------------------------------------------------------+
input group "=== SPEACE EA Parameters ==="
input double   LotSize_      = 0.1;          // Lotto trading
input int      StopLossPips_ = 500;          // Stop Loss in pips (5.0 per XAUUSD)
input int      TakeProfitPips_= 1000;         // Take Profit in pips (10.0 per XAUUSD)
input int      RSI_Period_   = 14;            // Periodo RSI
input int      MA_Fast_Period_= 10;           // Periodo MA veloce
input int      MA_Slow_Period_= 30;           // Periodo MA lenta
input int      MaxTrades_    = 3;            // Massimo trade simultanei
input double   MaxDrawdownPct_= 20.0;        // Drawdown massimo %
input int      MagicNumber   = 20260420;     // Identificatore EA
input int      TradeComment  = 1;             // 0=None 1=SPEACE 2=verbose

//+------------------------------------------------------------------+
//| Global mutable copies (updated by SPEACE at runtime)             |
//+------------------------------------------------------------------+
double   gLotSize          = 0.1;
int     gStopLossPips      = 500;
int     gTakeProfitPips    = 1000;
int     gRSI_Period         = 14;
int     gMA_Fast_Period    = 10;
int     gMA_Slow_Period    = 30;
int     gMaxTrades         = 3;
double  gMaxDrawdownPct    = 20.0;

//+------------------------------------------------------------------+
//| SPEACE State Files (JSON interface)                              |
//| Path = TERMINAL_DATA_PATH + SPEACE_RelativePath                |
//| Python reads from the same path.                                |
//+------------------------------------------------------------------+
input string   SPEACE_RelativePath = "speace-ea-integration\\shared_state\\";
input string   SPEACE_StateFile   = "ea_state.json";
input string   SPEACE_MetricsFile = "ea_metrics.json";
input string   SPEACE_ParamsFile  = "ea_params.json";

//+------------------------------------------------------------------+
//| Globals                                                          |
//+------------------------------------------------------------------+
struct TradeInfo {
    datetime open_time;
    double   open_price;
    double   lot;
    int      type;        // 0=BUY, 1=SELL
    double   pnl;
    bool     closed;
};

TradeInfo   g_trades[];
int         g_total_trades   = 0;
datetime    g_last_check     = 0;
double      g_initial_balance= 0.0;
datetime    g_session_start  = 0;
int         g_consecutive_loss= 0;
double      g_max_equity     = 0.0;
datetime    g_last_heartbeat = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit() {
    Print("SPEACE XAUUSD EA v1.00 initializing...");
    g_session_start    = TimeCurrent();
    g_last_heartbeat   = TimeCurrent();
    g_max_equity        = AccountInfoDouble(ACCOUNT_BALANCE);

    // Initialize runtime params from input defaults
    gLotSize         = LotSize_;
    gStopLossPips    = StopLossPips_;
    gTakeProfitPips  = TakeProfitPips_;
    gRSI_Period      = RSI_Period_;
    gMA_Fast_Period  = MA_Fast_Period_;
    gMA_Slow_Period  = MA_Slow_Period_;
    gMaxTrades       = MaxTrades_;
    gMaxDrawdownPct = MaxDrawdownPct_;

    if(StringLen(SPEACE_RelativePath) == 0) {
        Print("[SPEACE-WARNING] Shared path not set. SPEACE integration disabled.");
    }

    // Load parameters from SPEACE if available
    SPEACE_LoadParams();

    // Write initial metrics
    SPEACE_WriteMetrics();

    Print("SPEACE EA Init complete. Balance: ", AccountInfoDouble(ACCOUNT_BALANCE));
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    Print("SPEACE EA shutting down. Reason: ", reason);
    SPEACE_WriteMetrics();
}

//+------------------------------------------------------------------+
//| Main tick function                                                |
//+------------------------------------------------------------------+
void OnTick() {
    // Check every 5 seconds to avoid excessive load
    datetime now = TimeCurrent();
    if(now - g_last_check < 5) return;
    g_last_check = now;

    // Read updated parameters from SPEACE
    SPEACE_LoadParams();

    // Update equity high
    double equity = AccountInfoDouble(ACCOUNT_EQUITY);
    if(equity > g_max_equity) g_max_equity = equity;

    // Check drawdown protection
    if(!CheckDrawdownProtection()) return;

    // Check for trade signals
    int signal = GetTradeSignal();

    // Count open SPEACE trades
    int open_trades = CountOpenTrades();

    // Execute if signal and within limits
    if(signal != 0 && open_trades < gMaxTrades) {
        if(signal == 1 && open_trades == 0) { // BUY signal, no position
            OpenTrade(ORDER_TYPE_BUY);
        } else if(signal == -1 && open_trades == 0) { // SELL signal
            OpenTrade(ORDER_TYPE_SELL);
        }
    }

    // Manage open trades (trailing stop)
    ManageOpenTrades();

    // Heartbeat every 60 seconds
    if(now - g_last_heartbeat >= 60) {
        g_last_heartbeat = now;
        SPEACE_WriteMetrics();
        SPEACE_WriteState();
    }
}

//+------------------------------------------------------------------+
//| Signal Generation (RSI + Moving Average Crossover)               |
//+------------------------------------------------------------------+
int GetTradeSignal() {
    // RSI check
    double rsi = iRSI(_Symbol, PERIOD_CURRENT, gRSI_Period, PRICE_CLOSE);

    // Moving averages
    double ma_fast = iMA(_Symbol, PERIOD_CURRENT, gMA_Fast_Period, 0, MODE_EMA, PRICE_CLOSE);
    double ma_slow = iMA(_Symbol, PERIOD_CURRENT, gMA_Slow_Period, 0, MODE_EMA, PRICE_CLOSE);

    double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
    double spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * point;

    // BUY: RSI < 30 (oversold) AND MA_fast > MA_slow (uptrend)
    // SELL: RSI > 70 (overbought) AND MA_fast < MA_slow (downtrend)
    if(rsi < 30 && ma_fast > ma_slow) {
        return 1;  // BUY
    } else if(rsi > 70 && ma_fast < ma_slow) {
        return -1; // SELL
    }
    return 0;      // NO SIGNAL
}

//+------------------------------------------------------------------+
//| Open a new trade                                                  |
//+------------------------------------------------------------------+
bool OpenTrade(ENUM_ORDER_TYPE type) {
    double price, sl, tp;
    double lot = gLotSize;
    double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * point;

    if(type == ORDER_TYPE_BUY) {
        price = ask;
        sl    = NormalizeDouble(price - gStopLossPips * point, _Digits);
        tp    = NormalizeDouble(price + gTakeProfitPips * point, _Digits);
    } else {
        price = bid;
        sl    = NormalizeDouble(price + gStopLossPips * point, _Digits);
        tp    = NormalizeDouble(price - gTakeProfitPips * point, _Digits);
    }

    string comment = "";
    if(TradeComment == 1) comment = "SPEACE";
    else if(TradeComment == 2) comment = "SPEACE|RSI=" + DoubleToString(iRSI(_Symbol, PERIOD_CURRENT, gRSI_Period, PRICE_CLOSE), 1);

    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    request.action   = TRADE_ACTION_DEAL;
    request.symbol   = _Symbol;
    request.volume   = lot;
    request.type     = type;
    request.price    = price;
    request.sl       = sl;
    request.tp       = tp;
    request.deviation= 10;
    request.magic    = MagicNumber;
    request.comment  = comment;

    bool res = OrderSend(request, result);

    if(res) {
        g_total_trades++;
        if(TradeComment == 2) Print("[SPEACE] Trade opened: ", type == ORDER_TYPE_BUY ? "BUY" : "SELL",
            " @ ", price, " SL:", sl, " TP:", tp);
    } else {
        Print("[SPEACE-ERROR] OrderSend failed. Retcode: ", result.retcode,
              " Comment: ", result.comment);
    }

    return res;
}

//+------------------------------------------------------------------+
//| Trailing stop management                                          |
//+------------------------------------------------------------------+
void ManageOpenTrades() {
    double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

    for(int i = PositionsTotal() - 1; i >= 0; i--) {
        if(PositionGetSymbol(i) != _Symbol) continue;
        if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;

        ulong ticket = PositionGetTicket(i);
        double sl = PositionGetDouble(POSITION_SL);
        double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
        double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
        ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

        double trail_level = gStopLossPips / 2 * point;

        if(pos_type == POSITION_TYPE_BUY) {
            double new_sl = NormalizeDouble(current_price - trail_level, _Digits);
            if(new_sl > sl && sl > 0) {
                ModifyTrade(ticket, new_sl, PositionGetDouble(POSITION_TP));
            }
        } else if(pos_type == POSITION_TYPE_SELL) {
            double new_sl = NormalizeDouble(current_price + trail_level, _Digits);
            if(new_sl < sl || sl == 0) {
                ModifyTrade(ticket, new_sl, PositionGetDouble(POSITION_TP));
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Modify existing trade SL/TP                                       |
//+------------------------------------------------------------------+
bool ModifyTrade(ulong ticket, double new_sl, double tp) {
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    request.action  = TRADE_ACTION_SLTP;
    request.position = ticket;
    request.sl      = new_sl;
    request.tp      = tp;
    request.deviation= 10;
    bool res = OrderSend(request, result);
    if(!res) {
        Print("[SPEACE-ERROR] ModifyTrade failed. Ticket:", ticket);
    }
    return res;
}

//+------------------------------------------------------------------+
//| Count open SPEACE trades                                          |
//+------------------------------------------------------------------+
int CountOpenTrades() {
    int count = 0;
    for(int i = PositionsTotal() - 1; i >= 0; i--) {
        if(PositionGetSymbol(i) == _Symbol) {
            if(PositionGetInteger(POSITION_MAGIC) == MagicNumber) {
                count++;
            }
        }
    }
    return count;
}

//+------------------------------------------------------------------+
//| Drawdown protection                                                |
//+------------------------------------------------------------------+
bool CheckDrawdownProtection() {
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
    double drawdown_pct = ((balance - equity) / balance) * 100.0;

    if(drawdown_pct >= gMaxDrawdownPct) {
        // Close all positions
        CloseAllPositions();
        Print("[SPEACE-SAFETY] Max drawdown reached: ", drawdown_pct, "%. All positions closed.");
        return false;
    }

    // If equity is 50% of max equity, something is wrong - pause
    if(equity < g_max_equity * 0.5 && g_max_equity > 0) {
        Print("[SPEACE-WARNING] Equity significantly below peak. Pausing...");
        return false;
    }

    return true;
}

//+------------------------------------------------------------------+
//| Close all open positions                                         |
//+------------------------------------------------------------------+
void CloseAllPositions() {
    for(int i = PositionsTotal() - 1; i >= 0; i--) {
        if(PositionGetSymbol(i) == _Symbol) {
            if(PositionGetInteger(POSITION_MAGIC) == MagicNumber) {
                ulong ticket = PositionGetTicket(i);
                ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
                double lots = PositionGetDouble(POSITION_VOLUME);

                MqlTradeRequest request = {};
                MqlTradeResult result = {};
                request.action  = TRADE_ACTION_DEAL;
                request.symbol   = _Symbol;
                request.volume    = lots;
                request.type      = pos_type == POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
                request.position  = ticket;
                request.price     = SymbolInfoDouble(_Symbol, pos_type == POSITION_TYPE_BUY ? SYMBOL_BID : SYMBOL_ASK);
                request.deviation= 10;
                request.magic    = MagicNumber;

                if(!OrderSend(request, result)) {
                    Print("[SPEACE-ERROR] CloseAllPositions failed. Ticket:", ticket,
                          " Retcode:", result.retcode);
                }
            }
        }
    }
}

//+------------------------------------------------------------------+
//| SPEACE JSON Interface                                             |
//+------------------------------------------------------------------+
void SPEACE_LoadParams() {
    string filepath = TerminalInfoString(TERMINAL_DATA_PATH) + "\\" + SPEACE_RelativePath + SPEACE_ParamsFile;
    if(StringLen(SPEACE_RelativePath) == 0) return;

    int handle = FileOpen(filepath, FILE_READ | FILE_ANSI);
    if(handle == INVALID_HANDLE) return;

    string content = "";
    while(!FileIsEnding(handle)) {
        content += FileReadString(handle);
    }
    FileClose(handle);

    // Simple JSON parsing - look for specific values
    double v;

    if(JSON_Find(content, "\"LotSize\"", v)) {
        if(v > 0 && v <= 1.0) gLotSize = v;
    }
    if(JSON_Find(content, "\"StopLossPips\"", v)) {
        if(v >= 10 && v <= 5000) gStopLossPips = (int)v;
    }
    if(JSON_Find(content, "\"TakeProfitPips\"", v)) {
        if(v >= 10 && v <= 10000) gTakeProfitPips = (int)v;
    }
    if(JSON_Find(content, "\"RSI_Period\"", v)) {
        if(v >= 2 && v <= 100) gRSI_Period = (int)v;
    }
    if(JSON_Find(content, "\"MA_Fast_Period\"", v)) {
        if(v >= 2 && v <= 200) gMA_Fast_Period = (int)v;
    }
    if(JSON_Find(content, "\"MA_Slow_Period\"", v)) {
        if(v >= 5 && v <= 500) gMA_Slow_Period = (int)v;
    }
}

//+------------------------------------------------------------------+
//| Write current metrics to JSON (for SPEACE cortex)                 |
//+------------------------------------------------------------------+
void SPEACE_WriteMetrics() {
    string filepath = TerminalInfoString(TERMINAL_DATA_PATH) + "\\" + SPEACE_RelativePath + SPEACE_MetricsFile;
    if(StringLen(SPEACE_RelativePath) == 0) return;

    datetime now = TimeCurrent();
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
    double drawdown_pct = (g_max_equity > 0) ? ((g_max_equity - equity) / g_max_equity) * 100.0 : 0.0;
    int open_trades = CountOpenTrades();

    // Calculate win rate from history
    double win_rate = CalculateWinRate();

    string json = "{";
    json += "\"timestamp\":\"" + TimeToString(now, TIME_DATE | TIME_MINUTES | TIME_SECONDS) + "\",";
    json += "\"balance\":" + DoubleToString(balance, 2) + ",";
    json += "\"equity\":" + DoubleToString(equity, 2) + ",";
    json += "\"drawdown_pct\":" + DoubleToString(drawdown_pct, 2) + ",";
    json += "\"max_equity\":" + DoubleToString(g_max_equity, 2) + ",";
    json += "\"session_duration_min\":" + IntegerToString((now - g_session_start) / 60) + ",";
    json += "\"total_trades\":" + IntegerToString(g_total_trades) + ",";
    json += "\"open_trades\":" + IntegerToString(open_trades) + ",";
    json += "\"win_rate\":" + DoubleToString(win_rate, 4) + ",";
    json += "\"consecutive_loss\":" + IntegerToString(g_consecutive_loss) + ",";
    json += "\"rsi\":" + DoubleToString(iRSI(_Symbol, PERIOD_CURRENT, gRSI_Period, PRICE_CLOSE), 1) + ",";
    json += "\"ma_fast\":" + DoubleToString(iMA(_Symbol, PERIOD_CURRENT, gMA_Fast_Period, 0, MODE_EMA, PRICE_CLOSE), 5) + ",";
    json += "\"ma_slow\":" + DoubleToString(iMA(_Symbol, PERIOD_CURRENT, gMA_Slow_Period, 0, MODE_EMA, PRICE_CLOSE), 5) + ",";
    json += "\"bid\":" + DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_BID), 5) + ",";
    json += "\"ask\":" + DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_ASK), 5) + ",";
    json += "\"spread_pips\":" + DoubleToString(SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) / 10.0, 1);
    json += "}";

    int h = FileOpen(filepath, FILE_WRITE | FILE_ANSI | FILE_REWRITE);
    if(h != INVALID_HANDLE) {
        FileWriteString(h, json);
        FileClose(h);
    }
}

//+------------------------------------------------------------------+
//| Write EA state to JSON                                            |
//+------------------------------------------------------------------+
void SPEACE_WriteState() {
    string filepath = TerminalInfoString(TERMINAL_DATA_PATH) + "\\" + SPEACE_RelativePath + SPEACE_StateFile;
    if(StringLen(SPEACE_RelativePath) == 0) return;

    int open_trades = CountOpenTrades();

    string json = "{";
    json += "\"ea_name\":\"SPEACE_XAUUSD_EA\",";
    json += "\"version\":\"1.00\",";
    json += "\"timestamp\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES | TIME_SECONDS) + "\",";
    json += "\"mt5_account\":\"" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "\",";
    json += "\"account_balance\":" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + ",";
    json += "\"open_positions\":" + IntegerToString(open_trades) + ",";
    json += "\"params_loaded\":true,";
    json += "\"symbol\":\"" + _Symbol + "\",";
    json += "\"max_trades\":" + IntegerToString(gMaxTrades) + ",";
    json += "\"current_lot\":" + DoubleToString(gLotSize, 2) + ",";
    json += "\"stop_loss_pips\":" + IntegerToString(gStopLossPips) + ",";
    json += "\"take_profit_pips\":" + IntegerToString(gTakeProfitPips) + ",";
    json += "\"rsi_period\":" + IntegerToString(gRSI_Period) + ",";
    json += "\"ma_fast\":" + IntegerToString(gMA_Fast_Period) + ",";
    json += "\"ma_slow\":" + IntegerToString(gMA_Slow_Period);
    json += "}";

    int h = FileOpen(filepath, FILE_WRITE | FILE_ANSI | FILE_REWRITE);
    if(h != INVALID_HANDLE) {
        FileWriteString(h, json);
        FileClose(h);
    }
}

//+------------------------------------------------------------------+
//| Simple JSON value extractor (key must be quoted)                  |
//+------------------------------------------------------------------+
bool JSON_Find(const string& content, const string& key, double& value) {
    int pos = StringFind(content, key);
    if(pos < 0) return false;
    int colon = StringFind(content, ":", pos);
    if(colon < 0) return false;
    int start = colon + 1;
    while(start < StringLen(content) && (content[start] == ' ' || content[start] == ',' || content[start] == '}')) start++;
    int end = start;
    while(end < StringLen(content) && content[end] != ',' && content[end] != '}') end++;
    string val = StringSubstr(content, start, end - start);
    value = StringToDouble(val);
    return true;
}

//+------------------------------------------------------------------+
//| Calculate win rate from closed trades                             |
//+------------------------------------------------------------------+
double CalculateWinRate() {
    double total_pnl = 0;
    int winners = 0;
    int losers = 0;

    for(int i = HistoryDealsTotal() - 1; i >= 0; i--) {
        ulong ticket = HistoryDealGetTicket(i);
        if(HistoryDealGetInteger(ticket, DEAL_MAGIC) != MagicNumber) continue;

        double profit = HistoryDealGetDouble(ticket, DEAL_PROFIT);
        total_pnl += profit;
        if(profit > 0) winners++;
        else if(profit < 0) losers++;
    }

    int total = winners + losers;
    return (total > 0) ? (double)winners / total : 0.0;
}
//+------------------------------------------------------------------+
