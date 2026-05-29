--
-- PostgreSQL database dump
--

\restrict nayKR2qjod99dPInE1tN8LKItYGifxQcztnD1d2dVhlhqt407cqeanCOs3LeIax

-- Dumped from database version 16.13 (Debian 16.13-1.pgdg13+1)
-- Dumped by pg_dump version 16.13 (Debian 16.13-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: binance_api_keys; Type: TABLE; Schema: public; Owner: tradingbot
--

CREATE TABLE public.binance_api_keys (
    id integer NOT NULL,
    user_id integer NOT NULL,
    api_key_encrypted text NOT NULL,
    api_secret_encrypted text NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.binance_api_keys OWNER TO tradingbot;

--
-- Name: binance_api_keys_id_seq; Type: SEQUENCE; Schema: public; Owner: tradingbot
--

CREATE SEQUENCE public.binance_api_keys_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.binance_api_keys_id_seq OWNER TO tradingbot;

--
-- Name: binance_api_keys_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tradingbot
--

ALTER SEQUENCE public.binance_api_keys_id_seq OWNED BY public.binance_api_keys.id;


--
-- Name: bot_settings; Type: TABLE; Schema: public; Owner: tradingbot
--

CREATE TABLE public.bot_settings (
    id integer NOT NULL,
    user_id integer NOT NULL,
    enabled boolean NOT NULL,
    allowed_symbols character varying(500) NOT NULL,
    max_order_usdt double precision NOT NULL,
    max_daily_loss_usdt double precision NOT NULL,
    max_trades_per_day integer NOT NULL,
    telegram_enabled boolean NOT NULL,
    email_enabled boolean NOT NULL,
    stop_loss_pct double precision DEFAULT 0,
    take_profit_pct double precision DEFAULT 0,
    prevent_duplicate_positions boolean DEFAULT true,
    live_safety_confirmed boolean DEFAULT false
);


ALTER TABLE public.bot_settings OWNER TO tradingbot;

--
-- Name: bot_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: tradingbot
--

CREATE SEQUENCE public.bot_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bot_settings_id_seq OWNER TO tradingbot;

--
-- Name: bot_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tradingbot
--

ALTER SEQUENCE public.bot_settings_id_seq OWNED BY public.bot_settings.id;


--
-- Name: trade_logs; Type: TABLE; Schema: public; Owner: tradingbot
--

CREATE TABLE public.trade_logs (
    id integer NOT NULL,
    user_id integer NOT NULL,
    symbol character varying(50) NOT NULL,
    side character varying(10) NOT NULL,
    amount double precision NOT NULL,
    price double precision NOT NULL,
    notional_usdt double precision NOT NULL,
    status character varying(50) NOT NULL,
    mode character varying(20) NOT NULL,
    reason text NOT NULL,
    exchange_response text NOT NULL,
    created_at timestamp without time zone NOT NULL,
    pnl_usdt double precision DEFAULT 0,
    stop_loss_price double precision DEFAULT 0,
    take_profit_price double precision DEFAULT 0,
    protective_orders_status character varying(50) DEFAULT 'preview'::character varying
);


ALTER TABLE public.trade_logs OWNER TO tradingbot;

--
-- Name: trade_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: tradingbot
--

CREATE SEQUENCE public.trade_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.trade_logs_id_seq OWNER TO tradingbot;

--
-- Name: trade_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tradingbot
--

ALTER SEQUENCE public.trade_logs_id_seq OWNED BY public.trade_logs.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: tradingbot
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    is_admin boolean DEFAULT false
);


ALTER TABLE public.users OWNER TO tradingbot;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: tradingbot
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO tradingbot;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tradingbot
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: binance_api_keys id; Type: DEFAULT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.binance_api_keys ALTER COLUMN id SET DEFAULT nextval('public.binance_api_keys_id_seq'::regclass);


--
-- Name: bot_settings id; Type: DEFAULT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.bot_settings ALTER COLUMN id SET DEFAULT nextval('public.bot_settings_id_seq'::regclass);


--
-- Name: trade_logs id; Type: DEFAULT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.trade_logs ALTER COLUMN id SET DEFAULT nextval('public.trade_logs_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: binance_api_keys; Type: TABLE DATA; Schema: public; Owner: tradingbot
--

COPY public.binance_api_keys (id, user_id, api_key_encrypted, api_secret_encrypted, created_at) FROM stdin;
1	2	gAAAAABqGeDmXRsuw6E86fsbJ0DlXm8BM5tEwXeCfsY2mKEPTuO_wuLnuj738NsXA1enjX4Sc7heaA6kjoZvUamm14O0XK5xZ8SAbnu7zVh1RkXjzEDp43vCxnehL6tgc_t759n1mJKYHYYN-FxEJlEC7CLJmFFlUzL6PV1BzZ5lfb3G0Bh4KqM=	gAAAAABqGeDmX7f9e5WTfx-D0HpJvShSmB-1O3KPXvj_-YUPxTT08w3c0vRm3XVc3vnOTAxNN0vifOXrseg9g7dBupvDD_dfejNroNJuWybtKemDpkSzfDIo5S2yOrwd8tAX8T5yUYEgegyUYWLpnaF_D-6SebgD5OVK_J8f7aFX2ud1uFImRuc=	2026-05-29 18:54:30.698766
\.


--
-- Data for Name: bot_settings; Type: TABLE DATA; Schema: public; Owner: tradingbot
--

COPY public.bot_settings (id, user_id, enabled, allowed_symbols, max_order_usdt, max_daily_loss_usdt, max_trades_per_day, telegram_enabled, email_enabled, stop_loss_pct, take_profit_pct, prevent_duplicate_positions, live_safety_confirmed) FROM stdin;
4	4	f	BTC/USDT,ETH/USDT	25	20	3	t	t	0	0	t	f
2	2	t	BTC/USDT,ETH/USDT	25	20	10	t	t	0	0	t	f
\.


--
-- Data for Name: trade_logs; Type: TABLE DATA; Schema: public; Owner: tradingbot
--

COPY public.trade_logs (id, user_id, symbol, side, amount, price, notional_usdt, status, mode, reason, exchange_response, created_at, pnl_usdt, stop_loss_price, take_profit_price, protective_orders_status) FROM stdin;
1	2	BTC/USDT	BUY	0.1	100	10	simulated	dryrun	manual dryrun test	{"dryrun": true, "symbol": "BTC/USDT", "side": "buy", "amount": 0.1, "price": 100.0, "notional_usdt": 10.0, "status": "simulated"}	2026-05-29 05:22:35.582135	0	0	0	preview
2	2	BTC/USDT	BUY	0.1	100	10	simulated	dryrun	manual dryrun test	{"dryrun": true, "symbol": "BTC/USDT", "side": "buy", "amount": 0.1, "price": 100.0, "notional_usdt": 10.0, "status": "simulated"}	2026-05-29 05:57:27.769647	0	0	0	preview
3	2	BTC/USDT	BUY	0.00013	73350.29	10	closed	testnet	binance testnet test order	{"info": {"symbol": "BTCUSDT", "orderId": "8661758", "orderListId": "-1", "clientOrderId": "x-R4BD3S82e1d8763f1a47ab8c7d7443", "transactTime": "1780081114947", "price": "0.00000000", "origQty": "0.00013000", "executedQty": "0.00013000", "origQuoteOrderQty": "0.00000000", "cummulativeQuoteQty": "9.53553770", "status": "FILLED", "timeInForce": "GTC", "type": "MARKET", "side": "BUY", "workingTime": "1780081114947", "fills": [{"price": "73350.29000000", "qty": "0.00013000", "commission": "0.00000000", "commissionAsset": "BTC", "tradeId": "2670452"}], "selfTradePreventionMode": "EXPIRE_MAKER"}, "id": "8661758", "clientOrderId": "x-R4BD3S82e1d8763f1a47ab8c7d7443", "timestamp": 1780081114947, "datetime": "2026-05-29T18:58:34.947Z", "lastTradeTimestamp": 1780081114947, "lastUpdateTimestamp": 1780081114947, "symbol": "BTC/USDT", "type": "market", "timeInForce": "GTC", "postOnly": false, "reduceOnly": null, "side": "buy", "price": 73350.29, "triggerPrice": null, "amount": 0.00013, "cost": 9.5355377, "average": 73350.29, "filled": 0.00013, "remaining": 0.0, "status": "closed", "fee": {"currency": "BTC", "cost": 0.0}, "trades": [{"info": {"price": "73350.29000000", "qty": "0.00013000", "commission": "0.00000000", "commissionAsset": "BTC", "tradeId": "2670452"}, "timestamp": null, "datetime": null, "symbol": "BTC/USDT", "id": "2670452", "order": null, "type": null, "side": null, "takerOrMaker": null, "price": 73350.29, "amount": 0.00013, "cost": 9.5355377, "fee": {"currency": "BTC", "cost": 0.0}, "fees": [{"currency": "BTC", "cost": 0.0}]}], "fees": [{"currency": "BTC", "cost": 0.0}], "stopPrice": null, "takeProfitPrice": null, "stopLossPrice": null}	2026-05-29 18:58:35.091424	0	0	0	preview
4	2	ETH/USDT	BUY	0	0	10	rejected	testnet	Max trades per day reached		2026-05-29 20:23:41.317048	0	0	0	preview
5	2	ETH/USDT	SELL	0.0049	2023.13	10	closed	testnet	NDSP webhook real bridge test | NDSP Layer: layer-1 | Signal ID: webhook-test-003	{"info": {"symbol": "ETHUSDT", "orderId": "4522565", "orderListId": "-1", "clientOrderId": "x-R4BD3S829dbac87846397289f19877", "transactTime": "1780086347290", "price": "0.00000000", "origQty": "0.00490000", "executedQty": "0.00490000", "origQuoteOrderQty": "0.00000000", "cummulativeQuoteQty": "9.91333700", "status": "FILLED", "timeInForce": "GTC", "type": "MARKET", "side": "SELL", "workingTime": "1780086347290", "fills": [{"price": "2023.13000000", "qty": "0.00490000", "commission": "0.00000000", "commissionAsset": "USDT", "tradeId": "508805"}], "selfTradePreventionMode": "EXPIRE_MAKER"}, "id": "4522565", "clientOrderId": "x-R4BD3S829dbac87846397289f19877", "timestamp": 1780086347290, "datetime": "2026-05-29T20:25:47.290Z", "lastTradeTimestamp": 1780086347290, "lastUpdateTimestamp": 1780086347290, "symbol": "ETH/USDT", "type": "market", "timeInForce": "GTC", "postOnly": false, "reduceOnly": null, "side": "sell", "price": 2023.13, "triggerPrice": null, "amount": 0.0049, "cost": 9.913337, "average": 2023.13, "filled": 0.0049, "remaining": 0.0, "status": "closed", "fee": {"currency": "USDT", "cost": 0.0}, "trades": [{"info": {"price": "2023.13000000", "qty": "0.00490000", "commission": "0.00000000", "commissionAsset": "USDT", "tradeId": "508805"}, "timestamp": null, "datetime": null, "symbol": "ETH/USDT", "id": "508805", "order": null, "type": null, "side": null, "takerOrMaker": null, "price": 2023.13, "amount": 0.0049, "cost": 9.913337, "fee": {"currency": "USDT", "cost": 0.0}, "fees": [{"currency": "USDT", "cost": 0.0}]}], "fees": [{"currency": "USDT", "cost": 0.0}], "stopPrice": null, "takeProfitPrice": null, "stopLossPrice": null}	2026-05-29 20:25:47.442318	0	0	0	preview
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: tradingbot
--

COPY public.users (id, email, password_hash, is_active, created_at, is_admin) FROM stdin;
2	nawaf@example.com	$2b$12$lsW1aetrKv3FpFmPXO5DHevlp.yGKumf8KpbXjgsUvjMvdi2amFV.	t	2026-05-29 05:13:29.836547	t
4	Turki.89@hotmail.com	$2b$12$tKPc5r7rkgHxziwDhDWmiO/E3jFgGraP/PpJpfmBs1EIZu0k6cYwG	t	2026-05-29 20:14:20.106932	f
\.


--
-- Name: binance_api_keys_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tradingbot
--

SELECT pg_catalog.setval('public.binance_api_keys_id_seq', 1, true);


--
-- Name: bot_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tradingbot
--

SELECT pg_catalog.setval('public.bot_settings_id_seq', 4, true);


--
-- Name: trade_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tradingbot
--

SELECT pg_catalog.setval('public.trade_logs_id_seq', 5, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tradingbot
--

SELECT pg_catalog.setval('public.users_id_seq', 4, true);


--
-- Name: binance_api_keys binance_api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.binance_api_keys
    ADD CONSTRAINT binance_api_keys_pkey PRIMARY KEY (id);


--
-- Name: binance_api_keys binance_api_keys_user_id_key; Type: CONSTRAINT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.binance_api_keys
    ADD CONSTRAINT binance_api_keys_user_id_key UNIQUE (user_id);


--
-- Name: bot_settings bot_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.bot_settings
    ADD CONSTRAINT bot_settings_pkey PRIMARY KEY (id);


--
-- Name: bot_settings bot_settings_user_id_key; Type: CONSTRAINT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.bot_settings
    ADD CONSTRAINT bot_settings_user_id_key UNIQUE (user_id);


--
-- Name: trade_logs trade_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.trade_logs
    ADD CONSTRAINT trade_logs_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: tradingbot
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: tradingbot
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: binance_api_keys binance_api_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.binance_api_keys
    ADD CONSTRAINT binance_api_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: bot_settings bot_settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.bot_settings
    ADD CONSTRAINT bot_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: trade_logs trade_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tradingbot
--

ALTER TABLE ONLY public.trade_logs
    ADD CONSTRAINT trade_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict nayKR2qjod99dPInE1tN8LKItYGifxQcztnD1d2dVhlhqt407cqeanCOs3LeIax

