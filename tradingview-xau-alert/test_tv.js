const TradingView = require('@mathieuc/tradingview');

async function test() {
    const client = new TradingView.Client();
    const chart = new client.Session.Chart();
    
    chart.setMarket('OANDA:XAUUSD', {
        timeframe: '5',
        range: 500
    });

    chart.onUpdate(() => {
        if (!chart.periods.length) return;
        console.log(`Lấy được ${chart.periods.length} nến`);
        console.log('Nến mới nhất:', chart.periods[0]);
        client.end();
    });
}
test();
