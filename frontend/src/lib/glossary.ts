export const GLOSSARY: Record<string, { term: string; short: string; long: string }> = {
  cagr: {
    term: "CAGR",
    short: "Average yearly growth rate, as if growth were smooth.",
    long: "Compound Annual Growth Rate. If ₹100 became ₹200 in 7 years, the CAGR is about 10.4% — the steady yearly rate that would get you from start to finish. Real returns are bumpier.",
  },
  sip: {
    term: "SIP",
    short: "Investing a fixed amount every month.",
    long: "Systematic Investment Plan. You invest the same amount on a schedule, so you automatically buy more units when prices are low and fewer when they are high (rupee-cost averaging).",
  },
  lumpsum: {
    term: "Lump sum",
    short: "Investing the whole amount at once.",
    long: "A one-time investment. Its result depends heavily on the starting date — investing just before a fall feels very different from investing just after one.",
  },
  xirr: {
    term: "XIRR",
    short: "Yearly return that accounts for money added at different times.",
    long: "Extended Internal Rate of Return. For SIPs, each instalment is invested for a different length of time, so a simple CAGR doesn't work. XIRR finds the single yearly rate that explains all the cash flows.",
  },
  drawdown: {
    term: "Drawdown",
    short: "How far the price is below its previous peak.",
    long: "The percentage fall from the highest point reached so far. A max drawdown of −30% means that at its worst, an investor who bought at the peak was down 30%.",
  },
  volatility: {
    term: "Volatility",
    short: "How bumpy the ride is.",
    long: "The annualised standard deviation of daily returns. Higher volatility means bigger day-to-day swings. WealthLens labels below 10% as Low, 10–21% as Medium and above 21% as High risk. (For reference: the Nifty 50 has been around 20%, gold around 15–20%, USD/INR under 10%.)",
  },
  real_return: {
    term: "Real return",
    short: "Return after removing inflation.",
    long: "If your money grew 8% a year while prices rose 6% a year, your real return is about 1.9% — that's how much more you can actually buy.",
  },
  nav: {
    term: "NAV",
    short: "Price of one mutual fund unit.",
    long: "Net Asset Value: the value of everything the fund holds divided by the number of units. Published once a day after markets close.",
  },
  rolling: {
    term: "Rolling returns",
    short: "Returns for every possible holding period of a given length.",
    long: "Instead of one start date, rolling returns look at every 3-year (or 5-year) window in history. They show the range of outcomes a real investor could have had.",
  },
  win_rate: {
    term: "Win rate",
    short: "Share of past cases where the value was higher later.",
    long: "In the dip analyzer: of all the times an asset fell X% from its peak, the percentage where it was higher 1, 3 or 5 years later. History — not a promise.",
  },
  fd: {
    term: "FD",
    short: "Fixed deposit: a bank deposit at a fixed interest rate.",
    long: "WealthLens uses indicative 1-year FD rates from large Indian banks for each year as a low-risk benchmark (before tax).",
  },
  etf: {
    term: "ETF",
    short: "A fund you buy and sell on the stock exchange like a share.",
    long: "Exchange-Traded Fund. A gold ETF like GOLDBEES lets you own gold in your demat account without storing physical gold.",
  },
  index: {
    term: "Index",
    short: "A basket that tracks a part of the market.",
    long: "The Nifty 50, for example, tracks India's 50 largest listed companies. You can't buy an index directly, but index funds and ETFs copy it.",
  },
  elss: {
    term: "ELSS",
    short: "Tax-saving equity mutual fund with a 3-year lock-in.",
    long: "Equity Linked Savings Scheme. Investments qualify for deduction under Section 80C of the old tax regime, with the shortest lock-in among 80C options.",
  },
};
