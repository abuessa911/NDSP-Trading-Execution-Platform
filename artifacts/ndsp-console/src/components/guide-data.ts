export type Bi = { ar: string; en: string };
export type GuideChapter = { id: string; title: Bi; lead: Bi; items: Bi[]; href?: string };
const b = (ar: string,en: string): Bi => ({ar,en});

export const userGuide: GuideChapter[] = [
 {id:"workspace",title:b("إعدادات البوت الموحدة","Shared bot settings"),
 lead:b("بعد تسجيل الدخول يظهر شريط إعدادات واحد في جميع الصفحات، ويُحفظ اختيارك في الخادم لكل حساب.", "After sign-in one shared settings bar appears across all pages; choices are saved per account on the server."),
 items:[
 b("اختر الأصل والفريم والنمط المضاربي أو الاستثماري وطريقة التنفيذ والرافعة والهامش، ثم اضغط «تأكيد / تطبيق».", "Choose asset, timeframe, decision style, execution method, leverage and margin, then select Confirm / Apply."),
 b("الاختيارات قبل التأكيد مسودة فقط. بعد رسالة تأكيد الخادم تتبعها لوحة الشموع وبدء المراقبة وفحص الاستراتيجيات.", "Edits are drafts until the server confirms them. Verified candles and subsequent monitor/scanner starts then use the confirmed selection."),
 b("تطبيق الإعدادات يوقف المراقبة والفحص السابقين؛ أعد تشغيل ما تحتاجه بالإعداد الجديد لمنع خلط المخرجات.", "Applying settings stops previous monitoring and scans. Start the required monitor/scanners again with the new settings."),
 b("تُحفظ الرافعة من 1 إلى 125 وطريقة يدوي/آلي كتفضيلات، ولا تفتح صفقة أو تُغيّر رافعة حساب Binance.", "Leverage from 1 to 125 and manual/automatic method are saved preferences; they never open a trade or change Binance account leverage."),
 b("عند فشل تأكيد الحفظ تُخفى المخرجات السابقة. أعد تحميل الصفحة للتحقق من الحالة المحفوظة.", "If save confirmation fails, earlier outputs are hidden. Reload to verify the saved state.")],href:"/trading/"},

 {id:"start", title:b("البدء وتسجيل الدخول","Getting started and signing in"),
 lead:b("يمكن إنشاء حساب ذاتي عبر Keycloak والتحقق من البريد، دون دعوة، منفصلًا عن NDSP.","The bot supports verified-email self-registration in its own Keycloak realm, independent of NDSP."),
 items:[
 b("افتح bot.ndsp.app وأدخل بيانات البوابة الأولى عند طلبها؛ تختلف عن حساب Keycloak.","Open bot.ndsp.app and pass the first access gate; its credentials differ from Keycloak."),
 b("من «الدخول إلى الحساب» اختر تسجيل الدخول أو دخول المدير بالتحقق متعدد العوامل وفق صلاحيتك.","Use Account Access for regular sign-in or administrator password + TOTP sign-in."),
 b("تعتمد الجلسة على خادم البوت وملف ارتباط آمن، لا على رموز مخزنة محليًا في المتصفح.","The bot keeps its session server-side with a secure cookie, not locally stored provider tokens."),
 b("استخدم تحديث الجلسة عند الحاجة وتسجيل الخروج عند الانتهاء.","Use Refresh session as needed and Sign out when finished.")],href:"/account-access/"},
 {id:"navigation",title:b("القائمة واللغة وأنماط العرض","Navigation, language and display"),
 lead:b("القائمة الجانبية تتضمن القيادة والأسواق والتداول والمحفظة والتحليل والحساب.","The sidebar groups command, market, trading, portfolio, intelligence and account pages."),
 items:[
 b("افتح القائمة من زر ☰ على الجوال، واستخدم العربية أو الإنجليزية من الشريط العلوي.","Open ☰ on mobile, and switch Arabic or English in the header."),
 b("محاكاة/شبكة اختبار/مباشر تغيّر شكل العرض فقط ولا تختار بيئة تداول تشغيلية.","Simulation/Testnet/Live in the top strip only changes appearance, not the active trading environment."),
 b("وسوم تجريبي أو غير متصل أو معاينة تعني أن المحتوى ليس نتيجة تداول حقيقية.","DEMO/NOT CONNECTED/PREVIEW labels mean the content is not live execution evidence.")],href:"/"},
 {id:"command",title:b("مركز القيادة","Command center"),
 lead:b("يعرض حدود السلامة العامة وأمثلة توضيحية؛ لا يمنح صلاحية إرسال الأوامر.","Shows safety status and sample panels without permitting order execution."),
 items:[
 b("راجع توقف البوت واتصال البورصة وحالة المخاطر قبل تفسير أي رقم.","Read bot stopped, exchange connection and risk statuses before interpreting values."),
 b("قد تكون أرصدة الحساب والأداء والتعرض في المعاينة اصطناعية.","Preview balance, performance and exposure figures may be synthetic."),
 b("عبارة M1 غير مقبول تصف اعتماد المرحلة لا نجاح تسجيل الدخول وحده.","M1 NOT ACCEPTED is a milestone gate, separate from successful sign-in.")],href:"/"},
 {id:"market",title:b("الأسواق والشارت","Markets and chart"),
 lead:b("افصل بين قائمة الأسعار التجريبية ولوحة الشموع المقروءة من مصدر حقيقي عند توفرها.","Distinguish the mock watchlist from any independently sourced read-only candle panel."),
 items:[
 b("المفضلة في قائمة العينات محلية في المتصفح، والأسعار في القائمة ليست أسعار تنفيذ.","Demo watchlist favorites are browser-local and sample quotes are not executable prices."),
 b("تحقق من رمز الأصل والإطار الزمني والمصدر والحداثة قبل الاعتماد على أي شمعة للقراءة فقط.","Check symbol, timeframe, source and candle freshness before using read-only market data."),
 b("غياب بيانات سعرية حية أو صحيحة لا يبرر تفعيل التداول.","Missing valid live quotes never justify enabling trading.")],href:"/markets/"},
 {id:"profile",title:b("الاستثمار والمضاربة مقابل يدوي وآلي","Investment/speculation versus manual/automatic"),
 lead:b("اختيار استثماري أو مضاربي إعداد خاص بالبوت يُحفظ بعد إقرار Backend.","Investment or Speculation is a bot-owned preference acknowledged by its backend."),
 items:[
 b("اختر استثماري أو مضاربي من الشريط الموحد ثم اضغط تأكيد / تطبيق. الافتراضي مضاربي إن لم تحفظ اختيارًا.","Use the shared bar to choose Investment or Speculation, then Confirm / Apply. Speculation is the default until saved."),
 b("طريقة التنفيذ يدوي/آلي خيار مستقل يُحفظ على الخادم كتفضيل، دون تشغيل تداول.","Manual/Automatic is a separate server-saved preference and does not activate trading."),
 b("حفظ الشريط الموحد لا يرسل أمرًا. قسم تنفيذ Binance التجريبي مستقل وله إعداد وأزرار خاصة.","Saving shared settings sends no order. The Binance Demo execution section has independent setup and controls.")],href:"/trading/"},
 {id:"strategy",title:b("دليل الاستراتيجيات البحثية","Research strategies handbook"),
 lead:b("القواعد الخمس تُقيّم الشموع المغلقة فقط. لا توجد نتائج أداء معتمدة أو تنفيذ أوامر تلقائي بسبب ظهور مرشح بحثي.", "Five rules inspect closed candles only. Candidates do not imply validated performance or authorize orders."),
 items:[
 b("Trend Ladder: يستخدم EMA20 وEMA50 مع حركة آخر إغلاقين. شراء مرشح عندما EMA20 أعلى EMA50 والإغلاق الأخير صاعد؛ بيع مرشح للعكس. الإلغاء عند فقد شرط الاتجاه. لا يحدد وحده وقفًا أو هدفًا.", "Trend Ladder: EMA20 vs EMA50 plus last-two-close direction. Bullish when EMA20>EMA50 and close rises; bearish for the inverse. Candidate disappears when conditions fail. No embedded SL/TP."),
 b("Range Fade: يقيس قناة آخر 20 شمعة مكتملة باستثناء الحالية، بعرض لا يتجاوز 8% من الإغلاق. قرب الحد الأدنى 15% مرشح شراء، وقرب الأعلى مرشح بيع. الاختراق الشديد خطر على الاستراتيجية.", "Range Fade: 20-bar channel excluding current close, width <=8% of close. Within 15% of lower bound: long candidate; upper bound: short candidate. Breakouts are a major risk."),
 b("Breakout Scout: تجاوز أعلى/أدنى 20 شمعة سابقة مع حجم أكبر من متوسط حجمها يعطي مرشحًا اتجاهيًا. الاختراقات الكاذبة والانزلاق السعري مخاطر مهمة.", "Breakout Scout: close beyond prior 20-bar high/low plus volume above the 20-bar average yields a directional candidate. False breakouts and slippage matter."),
 b("Mean Return: يحسب متوسط إغلاق 20 شمعة سابقة وانحرافها المعياري. إغلاق أقل من متوسط ناقص 2σ مرشح شراء، وفوق المتوسط زائد 2σ مرشح بيع، إذا كان التباين أكبر من صفر.", "Mean Return: prior 20 closing-price mean and standard deviation. Below mean−2σ: long candidate; above mean+2σ: short candidate, with nonzero variance."),
 b("RSI Divergence V1: RSI14 بطريقة Wilder؛ قمم وقيعان سعر مؤكدة بثلاث شموع مغلقة على كل جانب. يقارن قمتين أو قاعين متتاليين، ويدعم التباعد العادي والخفي بشروط تغير سعر لا يقل عن 0.1% وتغير RSI لا يقل عن نقطتين. يفصل بين مرشح شراء وبيع؛ لا ينفذ تداولًا.", "RSI Divergence V1: Wilder RSI14 and strict price pivots confirmed by three CLOSED bars on either side. Compare last two pivots for regular or hidden divergence, price difference >=0.1%, RSI difference >=2 points. Research candidates only."),
 b("قيود الدايفرجنس: فصل القمم/القيعان بين 4 و35 شمعة، وصلاحية آخر قمة/قاع حتى 12 شمعة؛ مخرجات الاختبار غير معتمدة ولا توجد بعد فلاتر MACD/OBV/CCI أو وقف/هدف أو محرك أوامر.", "Divergence limits: pivot separation 4–35 bars, newest pivot at most 12 bars old; no approved performance, MACD/OBV/CCI confirmation, SL/TP or order routing."),
 b("لكل استراتيجية افحص حالات غير متاح ومحايد، مصدر البيانات، وقت إغلاق الشمعة، فشل المزود وحدود صلاحية الإشارة. اختبار تاريخي وخارج العينة مع احتساب الرسوم والانزلاق واختبار Shadow مطلوب قبل أي تفعيل تداول.", "For each strategy check unavailable/neutral status, data source, close time, provider failures and signal expiry. Backtesting, out-of-sample evaluation with fees/slippage and shadow validation are required before trade activation."),
 b("إعدادات الأصل والإطار والنمط والرافعة يتم تعديلها في صفحة التداول أو الإعدادات، لا من الدليل. الدليل قراءة فقط.", "Asset, timeframe, mode and leverage are changed in Trading/Settings, not inside this read-only handbook.")],href:"/strategies/"},
 {id:"testnet-execution",title:b("تنفيذ Binance Demo", "Binance Demo execution"),
 lead:b("قسم التداول يربط مفاتيح Demo المشفرة بمحرك أوامر تجريبي ذي سجل دائم؛ ولا يتيح تداول أموال حقيقية.", "Trading connects encrypted Demo keys to a durable exchange execution pilot; real-money trading remains unavailable."),
 items:[
 b("أنشئ مفتاح Binance Demo منفصلًا وأدخله في نموذج فحص Testnet. لا ترسل المفتاح أو السر في المحادثة. تُحذف بيانات النموذج بعد الإرسال وتبقى نسخة الخادم مشفرة لمدة 24 ساعة.", "Create a separate Binance Demo key and enter it in the Testnet connection form. Never paste keys into chat. Form fields clear after submission; encrypted server storage expires in 24 hours."),
 b("أكد أن العمليات لحساب Demo فقط ثم احفظ إعداد Testnet. القيم المعبأة للاختبار: BTCUSDT، فريم 15 دقيقة، EMA20/50 شراء فقط ورافعة 1×. هذا القسم مستقل عن شريط الإعدادات الموحدة والقواعد البحثية الأربع.", "Confirm Demo-only operations and save Testnet setup. Test defaults are BTCUSDT, 15 minutes, EMA20/50 long only and 1× leverage. This pilot is independent of shared settings and the four research rules."),
 b("اجعل حساب Demo في وضع One-way وSingle-Asset، ورافعة الأصل 1×، ونوع الهامش مطابقًا للإعداد. شغّل فحص الحساب ثم معاينة الإشارة؛ لا يُفتح مركز إن لم توجد إشارة دخول في شمعة مغلقة.", "Use One-way and Single-Asset modes, 1× symbol leverage and the saved margin type in Binance Demo. Run Preflight and Preview signal; no position opens without a closed-candle entry signal."),
 b("بعد الدخول استخدم فحص المركز والوقف ثم تسوية السجل. للإغلاق استخدم إغلاق مركز Testnet، ثم تنظيف الوقف بعد إثبات الإغلاق، ثم التسوية. لا تتكرر أوامر غامضة؛ استعد تأكيد الطلب نفسه أو تحقق من الدخول الغامض بإثباتات موقعة.", "After entry inspect the position and stop, then reconcile. For exit, close the Testnet position, clean its stop after verified closure, and reconcile. Ambiguous orders are never repeated; recover the same receipt or verify an uncertain entry from signed evidence."),
 b("للتشغيل الآلي اضغط «تشغيل الديمو آليًا لمدة ساعة». يستمر على الخادم، ويفتح عند التقاطع الصاعد ويغلق عند التقاطع الهابط أو حد الخسارة اليومية. انتهاء الساعة أو زر الإيقاف يوقف الدخول ويغلق المركز المثبت وينظف الوقف. الحالة الموقوفة للمراجعة لا تعيد أوامر غامضة تلقائيًا.", "Use Run Demo automatically for one hour. It continues on the server, enters on an upward cross and exits on a downward cross or daily loss limit. Expiry or Stop blocks new entries, closes a verified position and cleans its stop. Paused-for-review never retries uncertain orders automatically."),
 b("راقب نبضة الخادم والحالة. لا يبدأ تشغيل جديد إلا إذا تبقى للمفاتيح 75 دقيقة على الأقل. لا يمكن تغيير الإعداد أو استبدال المفاتيح أو حذفها أثناء التشغيل أو صفقة مفتوحة؛ تجديد المفتاح نفسه متاح. الرسوم وهوامش الانزلاق تدخل في الحجم ولا تضمن حدًا أقصى للخسارة.", "Monitor the server heartbeat and state. Starting requires at least 75 minutes of credential validity. Running automation or an open position blocks setup changes and key replacement/deletion; the same key can be renewed. Sizing includes fees and slippage buffers, without guaranteeing a maximum loss.")],href:"/trading/"},
 {id:"positions",title:b("تشغيل المحاكاة وسجل الحساب","Simulation and account ledger"),
 lead:b("صفحات المراكز والأوامر والصفقات والأداء تقرأ الآن سجل محاكاة خاصًا بحسابك؛ لا تقرأ رصيد Binance.","Positions, orders, history and performance now read your own durable simulation ledger, separate from Binance balances."),
 items:[
 b("أكد الإعدادات الموحدة أولًا. في صفحة التداول أدخل رأس مال افتراضيًا واختر قاعدة المحاكاة وحدود الخسارة والمخاطرة والهامش والوقف والهدف والرسوم والانزلاق ثم احفظ.","Confirm shared settings first. On Trading enter virtual capital, select a simulation rule, and set loss, risk, margin, stop, target, fee and slippage limits before saving."),
 b("الوضع اليدوي يتطلب كمية تختارها ثم شراء أو بيع افتراضي. الوضع الآلي يتطلب حفظ إعداد آلي ثم زر تشغيل المحاكاة؛ لا يبدأ بمجرد حفظ الشريط.","Manual mode requires your quantity and Virtual buy/short. Automatic mode requires saving automatic settings and explicitly starting the simulator; shared settings alone do not start it."),
 b("تستمر المراكز والرسوم والتعبئات بعد إعادة تشغيل الخدمة. لا يمكن محو الخسائر بإعادة ضبط رأس المال أو رفع حد الخسارة خلال يوم UTC نفسه.","Positions, fees and fills survive service restarts. Capital cannot be reset to erase losses, and the daily loss limit cannot increase within the same UTC day."),
 b("عند غموض تأكيد الأمر استخدم إعادة طلب التأكيد بنفس المعرف. لا تنشئ أمرًا بديلًا؛ الخادم يمنع التعبئة المكررة.","If an order acknowledgement is uncertain, retry confirmation with the same request ID. Do not replace it with another order; the server prevents duplicate fills.")],href:"/trading/"},
 {id:"performance",title:b("حدود نموذج المحاكاة","Simulation model limits"),
 lead:b("المحاكاة تعمل على الشموع المغلقة، ولا تمثل دفتر أوامر أو سيولة أو تنفيذ بورصة فعليًا.","Simulation uses completed candles; it does not reproduce exchange order books, liquidity or actual fills."),
 items:[
 b("يُسمح بمركز افتراضي واحد لكل حساب. تُفحص الحماية دوريًا؛ عند لمس الوقف والهدف في الشمعة نفسها يطبق الوقف أولًا، والفجوة عبر الوقف تستخدم السعر الأسوأ.","One virtual position is allowed per account. Protective checks run periodically; a candle hitting both exits uses the stop first, and gaps through stops use the worse price."),
 b("عند غياب السعر الصحيح تُخفى قيمة المركز الحالية وتتوقف الإدخالات الآلية. انقطاع تسلسل الشموع يوقف الآلي ولا يختلق تعبئات تاريخية.","Missing verified quotes hide current position equity and stop automatic entries. Candle history gaps halt automation without inventing historical fills."),
 b("إيقاف الإدخالات يترك فحص الوقف والهدف للمركز الافتراضي المفتوح قائمًا. تغيير الإعدادات يوقف الآلي ويحتاج إعادة حفظ حساب المحاكاة وهو بلا مركز مفتوح.","Stopping entries keeps protective checks for an existing virtual position. Changing settings stops automation; reconfigure the simulation account while flat."),
 b("هذه نتائج أموال افتراضية فقط. التداول الحي وربط قرار NDSP الإنتاجي لم يُعتمدا.","These are virtual-fund results only. Live execution and production NDSP decision intake remain uncertified.")],href:"/performance/"},
 {id:"decisions",title:b("قرارات NDSP وتتبّع التنفيذ","NDSP decisions and execution trace"),
 lead:b("NDSP والبوت منفصلان؛ مسار القرارات الإنتاجي الموقّع لم يُعتمد بعد.","NDSP and the bot are separate; production signed-decision intake remains unapproved."),
 items:[
 b("NDSP-NEX-1.0 عقد مخطط يخضع للتحقق من التوقيع والنسخة والحداثة والهوية.","NDSP-NEX-1.0 is a proposed signed contract requiring version, signature, freshness and identity proof."),
 b("القرارات وآثار التنفيذ الموجودة في المعاينة ليست قرارات NDSP إنتاجية.","Demo decision lifecycle and execution trace are not production NDSP decisions."),
 b("اختيار مضاربي أو استثماري في البوت لا يغيّر عقد NDSP ولا ينقل أسراره.","The bot decision profile does not amend the NDSP contract or expose its internals.")],href:"/ndsp-decisions/"},
 {id:"replay",title:b("مختبر الإعادة","Replay lab"),
 lead:b("الخط الزمني الحالي اصطناعي وليس اختبارًا تاريخيًا معتمدًا.","The current replay timeline is synthetic, not a certified historical backtest."),
 items:[
 b("يمكن تشغيل العينة وإيقافها والتنقل عبر خطواتها لتجربة الواجهة.","Play, pause and scrub the sample to explore the UI."),
 b("لا تستخدم العينات لإثبات أداء أي استراتيجية في سوق فعلي.","Do not use replay samples as evidence of actual trading performance.")],href:"/replay-lab/"},
 {id:"connections",title:b("Binance والتنبيهات","Binance and notifications"),
 lead:b("شاشات الموصل والإشعارات لا تعني وجود قناة تداول أو إرسال مفعّلة.","Connector and notification previews do not establish an active trade or messaging channel."),
 items:[
 b("لا تدخل مفاتيح API أو كلمة المرور أو رمز TOTP في أي حقول تجريبية.","Never enter API keys, passwords or TOTP into sample forms."),
 b("تحقق من حالة الموصل عبر Backend معتمد قبل اعتبار البورصة متصلة.","Only authoritative backend diagnostics can confirm exchange connectivity."),
 b("قراءة أو إقرار التنبيه في المعاينة محلي ولا يرسل بريدًا بالضرورة.","Preview alert acknowledgement is local and does not necessarily send email.")],href:"/binance-connection/"},
 {id:"account",title:b("الحساب والإعدادات والاشتراك","Account, settings and subscription"),
 lead:b("الصلاحيات الحقيقية معتمدة من الخادم، بينما تفضيلات العرض محلية.","Actual permissions are server-authoritative; display preferences are local."),
 items:[
 b("يمكن تغيير بعض تفضيلات اللغة والعرض في المتصفح دون تعديل MFA أو صلاحيات الحساب.","Some browser display preferences can be changed without modifying MFA or server roles."),
 b("تعرض الاشتراكات الصلاحيات، لكن الدفع وإدارة الباقات والفواتير ليست جاهزة في M1.","Subscription shows entitlements; billing, checkout and plan management are absent from M1."),
 b("عند ظهور 401 سجّل الدخول مجددًا؛ أما 403 فيعني عدم استيفاء شروط الوصول.","For 401 sign in again; 403 indicates a denied permission or assurance requirement.")],href:"/subscription/"},
 {id:"troubleshoot",title:b("المساعدة والأعطال","Troubleshooting"),
 lead:b("فرّق بين خلل عرض المتصفح وفشل الجلسة أو خدمة Backend.","Separate browser display errors from session failures and backend outages."),
 items:[
 b("حدّث الصفحة كاملة إذا لم يظهر التحديث، ثم اختر اللغة المطلوبة.","Hard refresh if changes do not appear, then choose the required language."),
 b("افحص صحة الخدمات والتاريخ ورسالة الخطأ قبل طلب الإصلاح.","Inspect service health, timestamp and error reason before requesting a fix."),
 b("لا ترسل بيانات حساسة أو ملفات جلسة ضمن الصور والتقارير.","Never share secrets, cookies or private session data in screenshots or reports.")],href:"/health/"},
];

export const ownerGuide: GuideChapter[] = [
 {id:"workspace-operations",title:b("تشغيل الإعدادات الموحدة","Operating shared settings"),
 lead:b("الإعدادات والمراقبة والفحص معزولة بحسب المستخدم والمستأجر؛ ولا يرفع حفظها حظر الأوامر.", "Settings, monitoring and scans are scoped per user and tenant; saving them never lifts the order execution block."),
 items:[
 b("حفظ الإعدادات وإبطال نتائج المراقبة والفحص السابقين عملية Redis ذرّية.", "Settings and invalidation of previous monitor/scanner results are committed atomically in Redis."),
 b("إذا تغير الاختيار أثناء جلب السوق يُرفض تشغيل الإعداد السابق برسالة WORKSPACE_CHANGED_RETRY؛ حدّث الحالة وحاول مجددًا.", "If settings change during a market read, starting the old selection returns WORKSPACE_CHANGED_RETRY; refresh and retry."),
 b("تُرفض الرافعة غير الصحيحة وغياب CSRF والجلسة وفساد التخزين؛ لا تُستخدم أسعار بديلة اصطناعية.", "Invalid leverage, missing session/CSRF and corrupted state are rejected; synthetic fallback prices are never used."),
 b("اختبار إعدادات البوت لا يثبت اعتماد NDSP أو جاهزية محرك تداول حي.", "Workspace tests do not certify NDSP integration or a live trading engine.")],href:"/trading/"},

 {id:"boundary",title:b("استقلال البوت ومنصة NDSP","Bot and NDSP separation"),
 lead:b("أنظمة الهوية والبيانات والخدمات مستقلة، والرابط الوحيد مستقبلًا عقد قرار التداول المعتمد.","Identity, databases and services stay separate; the only future link is an approved signed decision contract."),
 items:[
 b("لا توحّد قاعدة بيانات NDSP مع البوت ولا تعيد استخدام جلسة الإدارة أو خدمات الاشتراك.","Do not merge NDSP databases or reuse its admin sessions or billing services."),
 b("لا يُستهلك قرار NDSP إنتاجي حتى تثبيت NDSP-NEX-1.0 ومصدر موثوق وتوقيع ومطابقة المستأجر.","No production NDSP decision is accepted before a trusted NDSP-NEX-1.0 issuer, signature and tenant mapping."),
 b("التواقيع الاصطناعية للاختبار لا تمنح إذن تنفيذ.","Synthetic test signatures do not grant execution authority.")]},
 {id:"owner-access",title:b("دخول المالك والتحقق الثنائي","Owner sign-in and MFA"),
 lead:b("يجب أن تتحقق المصادقة بكلمة المرور وTOTP وصلاحيات الخادم معًا.","Authentication requires password, TOTP and authoritative server role checks."),
 items:[
 b("استخدم «دخول المدير بالتحقق متعدد العوامل» وتأكد من ظهور ADMIN بعد العودة.","Use Administrator MFA sign-in and confirm ADMIN after the callback."),
 b("اختبر تحديث الجلسة بعد انتهاء رمز الوصول ورفض العمليات المحمية بعد الخروج.","Verify access-token-expiry refresh and denial of privileged operations after logout."),
 b("لا تضع كلمة مرور أو TOTP أو رمز جلسة في سجل أو محادثة.","Keep passwords, TOTP and session tokens out of logs and chat.")],href:"/account-access/"},
 {id:"user-admin",title:b("إدارة المستخدمين والدعوات","Users, tenants and invitations"),
 lead:b("الإنشاء العام للحسابات معطّل والدعوات محكومة بصلاحية المدير.","Public registration is disabled and invitations require server-verified admin authority."),
 items:[
 b("أنشئ طلب تسجيل معلّق عند الصلاحية ولا تجمع كلمة مرور الشخص المدعو.","Create pending registrations only when authorized and never collect invited users' passwords."),
 b("التحقق من البريد شرط مستقل لتفعيل حساب مستخدم جديد.","Email verification is a separate prerequisite for activation."),
 b("راجع المستأجر والدور وسجل التدقيق، ولا تعتبر الطلب المعلق حسابًا نشطًا.","Check tenant, role and audit; a pending request is not an active user."),
 b("لا تفترض إرسال رسائل الدعوة تلقائيًا إلا إذا ثبت إعداد SMTP ومسار الإرسال.","Do not assume automatic invitation email without verified SMTP and dispatch.")],href:"/admin/users-tenants/"},
 {id:"accept-m1",title:b("بوابات قبول M1","M1 acceptance gates"),
 lead:b("جاهزية PostgreSQL وRedis وOIDC ليست وحدها قبولًا نهائيًا.","Healthy PostgreSQL, Redis and OIDC are not sufficient for final acceptance."),
 items:[
 b("أثبت تسجيل الدخول الفعلي وMFA وCSRF وعزل المستأجرين والصلاحيات والتدقيق والخروج.","Prove real-browser MFA, CSRF, tenant isolation, permissions, audit and logout."),
 b("اعتماد M1 مستقل عن نجاح بناء الصفحات وعن وجود دور ADMIN.","M1 certification is separate from successful static builds or an ADMIN label."),
 b("احتفظ بأدلة PASS/FAIL وخطط التراجع قبل توقيع قبول المرحلة.","Retain PASS/FAIL evidence and rollback plans before marking the milestone accepted.")],href:"/admin/operations-center/"},
 {id:"ops",title:b("صحة الخدمات والتشغيل","Service operation and observability"),
 lead:b("التشغيل الآمن يتطلب جاهزية حقيقية ومراقبة وإغلاقًا آمنًا عند الفشل.","Safe operation requires genuine readiness, monitoring and fail-closed behavior."),
 items:[
 b("راقب حالة API وKeycloak وRedis وPostgreSQL والوكيل العكسي من مصادرها الفعلية.","Monitor API, Keycloak, Redis, PostgreSQL and gateway from real authoritative sources."),
 b("السجلات بتوقيت UTC؛ احذر عرض الأسرار والمفاتيح في مخرجات التشخيص.","Use UTC audit times and redact secrets in diagnostics."),
 b("الرمز 200 لا يثبت وجود صلاحية تداول أو جاهزية أموال حقيقية.","HTTP 200 does not prove trading authorization or funded account readiness.")],href:"/health/"},
 {id:"safety",title:b("حدود المخاطر والإيقاف الاضطراري","Risk controls and emergency stop"),
 lead:b("التداول الحي معطّل والإيقاف العام مفعل إلى حين اعتماد مستقل.","Live trading remains disabled with a global kill switch until separate approval."),
 items:[
 b("حافظ على LIVE_TRADING_ENABLED=false وGLOBAL_KILL_SWITCH=true وBINANCE_ALLOW_WITHDRAW=false.","Keep LIVE_TRADING_ENABLED=false, GLOBAL_KILL_SWITCH=true and BINANCE_ALLOW_WITHDRAW=false."),
 b("لا تفسر اختيار مباشر أو زر شراء بوصفه رفعًا للحماية.","Neither a Live UI appearance nor a Buy button overrides the safety boundary."),
 b("تشغيل البورصة يتطلب موافقات وحدود مراكز وخسارة ورافعة وتأكيدا يدويا واختبارات.","Exchange activation requires approved exposure, loss, leverage, confirmations and testing.")],href:"/admin/trading-safety/"},
 {id:"decision",title:b("نمط الاستثمار والمضاربة والعقد","Decision profiles and contract rules"),
 lead:b("نمط التداول المحفوظ حاليًا إعداد بوت فقط، منفصل عن طريقة تنفيذ يدوي/آلي.","The saved decision profile is bot-owned and separate from manual/automatic execution."),
 items:[
 b("إعداد استثماري/مضاربي محفوظ لكل مستخدم ومستأجر مع مصادقة وCSRF.","Investment/Speculation preferences are user/tenant-scoped with authentication and CSRF."),
 b("لم يُضاف هذا الحقل إلى NDSP-NEX-1.0 المجمّد.","This field has not been added to the frozen NDSP-NEX-1.0 schema."),
 b("أي تعديل للعقد يحتاج نسخة واعتماد توقيع وتوافق المرسل والمستقبل.","Contract changes require versioning, signed profile approval and producer/consumer compatibility.")],href:"/trading/"},
 {id:"roadmap",title:b("وظائف لم تنفذ بعد","Capabilities not yet implemented"),
 lead:b("وجود زر في الواجهة لا يعني وجود محرك على الخادم.","Visible controls do not imply a running backend engine."),
 items:[
 b("الأوامر والمراكز والصفقات والأداء تأتي من سجل المحاكاة؛ بطاقات الاستراتيجيات وبعض الأقسام الأخرى تبقى عينات موسومة.","Orders, positions, history and performance read the simulation ledger; strategy cards and some other sections remain labelled samples."),
 b("محرك المحاكاة ودفتره مفعّلان بمعزل عن موصل التنفيذ الحقيقي وNDSP.","The simulation engine and ledger operate independently of live exchange adapters and NDSP."),
 b("لا تُزل ملصق «تجريبي» دون توثيق endpoint وصلاحية وتخزين واختبار حي.","Never remove DEMO labels without a proven API, authorization, persistence and E2E test.")]},
 {id:"market",title:b("بيانات السوق والوسطاء","Market data and exchange connectors"),
 lead:b("لوحة شموع للقراءة فقط ليست موصل تنفيذ حقيقيًا.","A read-only candle source is not a live execution adapter."),
 items:[
 b("تحقق من حداثة السعر والرمز والإطار الزمني والمصدر، وارفض الأسعار الصفرية أو المنقطعة.","Validate price freshness, symbol, timeframe and source; reject stale or zero quotes."),
 b("لا تدخل مفاتيح Binance الحقيقية في إعداد تجريبي، واحظر السحب دائمًا.","Never put live Binance API keys in demo forms, and prohibit withdrawals."),
 b("يتطلب موصل الإنتاج صلاحيات دنيا وتقييد IP وتسوية الأوامر والتعامل مع الانقطاع.","Production adapters need least privilege, IP restrictions, reconciliation and outage handling.")],href:"/admin/exchange-health/"},
 {id:"ndsp",title:b("حَوْكمة استقبال قرار NDSP","Governed NDSP decision ingestion"),
 lead:b("الاعتماد الإنتاجي للعقد والتوقيع وموثوقية المنشأ لم يكتمل بعد.","Production trust for the contract, signature and source provenance is not certified."),
 items:[
 b("تحقق من UUID والإصدار والتوقيع والوقت والمستأجر ومصدر القرار ومنع إعادة التشغيل.","Verify decision identity, version, signature, time, tenant, origin and replay protection."),
 b("لا تُنسخ تفاصيل طبقات NDSP وخوارزميات TDL/NMP المحمية إلى البوت.","Do not copy NDSP protected TDL/NMP internals to the bot."),
 b("الاختبارات الاصطناعية لا تسمح بتحويل أي إشارة إلى أمر حقيقي.","Synthetic vectors must never be promoted into real orders.")],href:"/admin/ndsp-health/"},
 {id:"admin-audit",title:b("التدقيق وأقسام الإدارة","Admin API and audit"),
 lead:b("واجهات الإدارة الحقيقية للقراءة المحمية، وبعض الوظائف مصنّفة NOT_IMPLEMENTED.","Protected admin read endpoints exist; some capabilities explicitly report NOT_IMPLEMENTED."),
 items:[
 b("راجع صلاحيات المستخدمين وسجلات التدقيق وحالة الخدمات بواجهة مدير تحققت من MFA.","Use MFA-protected views to check users, audit events and service status."),
 b("اختبر 401 و403 وعزل المستأجر عند كل إضافة؛ إخفاء رابط القائمة ليس صلاحية.","Test 401/403 and tenant isolation for new actions; hidden navigation is not access control."),
 b("عدم وجود فواتير أو إشعارات أو مهام خلفية جاهزة يجب أن يظهر صراحة لا أن يختبئ خلف بيانات عينة.","Missing billing, notification or worker backends must be reported explicitly, never masked by sample data.")],href:"/admin/audit/"},
 {id:"release",title:b("النشر والنسخ الاحتياطية والتراجع","Deployment, backups and rollback"),
 lead:b("أي نشر يجب أن يقتصر على خدمات البوت ولا يلمس NDSP.","Every release must remain within bot-only services and leave NDSP untouched."),
 items:[
 b("خذ نسخة من شجرة الواجهة المنشورة ومكونات API قبل الاستبدال.","Back up the deployed static UI tree and touched API components before swapping."),
 b("نفّذ اختبارات Backend والواجهة وTypeScript وبناء Next.js ثم فحص HTTP والصلاحيات.","Run backend, frontend, TypeScript and Next.js build tests, followed by HTTP/security smoke checks."),
 b("أعد النسخة السابقة عند فشل اختبار، ووثّق مسارات التراجع وحالة الخدمات.","Roll back on failed gates and document rollback paths and service status."),
 b("لا تظهر كلمات مرور قواعد البيانات وSMTP في السجلات.","Never log database or SMTP secrets.")]},
 {id:"incidents",title:b("الأعطال والاسترداد","Incidents and recovery"),
 lead:b("أي فقد اتصال أو هوية أو سعر يؤدي إلى رفض آمن لا إلى فتح التداول.","Loss of identity, data or service must fail closed."),
 items:[
 b("عند انتهاء رمز Keycloak افحص مسار تحديث الجلسة وسجل السبب دون تعطيل MFA.","For expired Keycloak tokens, inspect refresh and audit without disabling MFA."),
 b("إذا توقفت Redis أو قاعدة البيانات أو بيانات السوق لا تُشغّل التداول كحل مؤقت.","Never enable trading as a workaround for Redis, database or market-data outages."),
 b("استعد من نسخة موثقة وأعد فحص RLS والهوية والتدقيق قبل اعتماد العودة.","Restore from verified backups and recheck RLS, identity and audit.")],href:"/admin/incidents/"},
 {id:"owner-check",title:b("قائمة القبول الشخصي","Personal operation checklist"),
 lead:b("السماح بتصفح البوت لا يساوي السماح بتداول أموال حقيقية.","Personal access to the bot is not authorization to trade real funds."),
 items:[
 b("تأكد من دخول المالك بـTOTP وتحديث الجلسة ورفض الدخول بعد الخروج.","Verify owner TOTP login, refresh and post-logout access denial."),
 b("تأكد من عمل API المحمي وحماية CSRF والتدقيق وعزل المستأجر.","Verify authenticated APIs, CSRF, audit and tenant boundaries."),
 b("أثبت أن العينات والمحاكاة وBinance Demo واضحة ومنفصلة، وأن أوامر Mainnet ما زالت محظورة.","Verify separate, clear labels for samples, simulation and Binance Demo; Mainnet orders must remain blocked."),
 b("وقّع اعتماد التداول الورقي والعقد الإنتاجي والتداول الحقيقي كمراحل منفصلة لاحقًا.","Approve paper execution, the production decision contract and real trading as separate future gates.")]},
];
