--
-- PostgreSQL database dump
--

\restrict 23uAQFNJexqZEXC8dRP2jhxIsJFjHd5u3Eeh3n7TWuoLYXTtC2OBE9XIcTHJ8rG

-- Dumped from database version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)

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

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: telegrambot
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO telegrambot;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: telegrambot
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO telegrambot;

--
-- Name: certificates; Type: TABLE; Schema: public; Owner: telegrambot
--

CREATE TABLE public.certificates (
    id integer NOT NULL,
    cert_id bigint NOT NULL,
    file_path character varying(500) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    user_id integer NOT NULL,
    status character varying(50) NOT NULL
);


ALTER TABLE public.certificates OWNER TO telegrambot;

--
-- Name: certificates_id_seq; Type: SEQUENCE; Schema: public; Owner: telegrambot
--

CREATE SEQUENCE public.certificates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.certificates_id_seq OWNER TO telegrambot;

--
-- Name: certificates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: telegrambot
--

ALTER SEQUENCE public.certificates_id_seq OWNED BY public.certificates.id;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: telegrambot
--

CREATE TABLE public.orders (
    id integer NOT NULL,
    user_id integer NOT NULL,
    telegram_id bigint NOT NULL,
    tariff_code character varying(20) NOT NULL,
    days integer NOT NULL,
    status character varying(50) NOT NULL,
    amount integer,
    payment_id character varying(255),
    created_at timestamp with time zone NOT NULL,
    paid_at timestamp with time zone,
    reminders_sent integer DEFAULT 0 NOT NULL,
    last_reminder_at timestamp with time zone,
    subscription_id integer,
    action character varying(20) DEFAULT 'buy'::character varying NOT NULL,
    cer_id character varying(64),
    public_order_id character varying(32),
    payment_url character varying(1000),
    payment_status character varying(50),
    customer_email character varying(255)
);


ALTER TABLE public.orders OWNER TO telegrambot;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: public; Owner: telegrambot
--

CREATE SEQUENCE public.orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.orders_id_seq OWNER TO telegrambot;

--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: telegrambot
--

ALTER SEQUENCE public.orders_id_seq OWNED BY public.orders.id;


--
-- Name: referrals; Type: TABLE; Schema: public; Owner: telegrambot
--

CREATE TABLE public.referrals (
    id integer NOT NULL,
    referrer_telegram_id bigint NOT NULL,
    referred_telegram_id bigint NOT NULL,
    status character varying(50) NOT NULL,
    reward_days integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    rewarded_at timestamp with time zone
);


ALTER TABLE public.referrals OWNER TO telegrambot;

--
-- Name: referrals_id_seq; Type: SEQUENCE; Schema: public; Owner: telegrambot
--

CREATE SEQUENCE public.referrals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.referrals_id_seq OWNER TO telegrambot;

--
-- Name: referrals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: telegrambot
--

ALTER SEQUENCE public.referrals_id_seq OWNED BY public.referrals.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: telegrambot
--

CREATE TABLE public.users (
    id integer NOT NULL,
    telegram_id bigint NOT NULL,
    username character varying(255),
    created_at timestamp without time zone NOT NULL,
    first_name character varying(255),
    is_active boolean DEFAULT true NOT NULL,
    subscription_until timestamp with time zone
);


ALTER TABLE public.users OWNER TO telegrambot;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: telegrambot
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO telegrambot;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: telegrambot
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: vpn_subscriptions; Type: TABLE; Schema: public; Owner: telegrambot
--

CREATE TABLE public.vpn_subscriptions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    telegram_id bigint NOT NULL,
    cer_id character varying(64) NOT NULL,
    cert_path character varying(500),
    status character varying(50) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    paid_at timestamp with time zone,
    expires_at timestamp with time zone,
    tariff_code character varying(20),
    identity_enabled boolean DEFAULT false NOT NULL,
    cert_created_at timestamp with time zone,
    cert_expires_at timestamp with time zone,
    reminded_7d boolean DEFAULT false NOT NULL,
    reminded_3d boolean DEFAULT false NOT NULL,
    reminded_1d boolean DEFAULT false NOT NULL,
    cert_sent_at timestamp with time zone
);


ALTER TABLE public.vpn_subscriptions OWNER TO telegrambot;

--
-- Name: vpn_subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: telegrambot
--

CREATE SEQUENCE public.vpn_subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vpn_subscriptions_id_seq OWNER TO telegrambot;

--
-- Name: vpn_subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: telegrambot
--

ALTER SEQUENCE public.vpn_subscriptions_id_seq OWNED BY public.vpn_subscriptions.id;


--
-- Name: certificates id; Type: DEFAULT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.certificates ALTER COLUMN id SET DEFAULT nextval('public.certificates_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.orders ALTER COLUMN id SET DEFAULT nextval('public.orders_id_seq'::regclass);


--
-- Name: referrals id; Type: DEFAULT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.referrals ALTER COLUMN id SET DEFAULT nextval('public.referrals_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: vpn_subscriptions id; Type: DEFAULT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.vpn_subscriptions ALTER COLUMN id SET DEFAULT nextval('public.vpn_subscriptions_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: telegrambot
--

COPY public.alembic_version (version_num) FROM stdin;
4248fa14bfbb
\.


--
-- Data for Name: certificates; Type: TABLE DATA; Schema: public; Owner: telegrambot
--

COPY public.certificates (id, cert_id, file_path, is_active, created_at, user_id, status) FROM stdin;
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: telegrambot
--

COPY public.orders (id, user_id, telegram_id, tariff_code, days, status, amount, payment_id, created_at, paid_at, reminders_sent, last_reminder_at, subscription_id, action, cer_id, public_order_id, payment_url, payment_status, customer_email) FROM stdin;
1	1	795564969	1m	31	paid	500	8444823542	2026-05-04 23:24:53.799724+00	2026-05-04 23:25:50.158253+00	0	\N	1	buy	795564969	5463	https://pay.tbank.ru/6c5Euzc6	CONFIRMED	\N
16	19	1056461560	1m	31	paid	500	8453347548	2026-05-06 10:25:32.584959+00	2026-05-06 10:29:54.869241+00	0	\N	20	buy	1056461560	6386	https://pay.tbank.ru/AZvCIssq	CONFIRMED	valek.bondarchuk.2014@bk.ru
17	28	5620912112	1m	31	paid	500	8466083288	2026-05-08 12:01:12.139254+00	2026-05-08 12:01:57.156021+00	0	\N	21	buy	5620912112	3704	https://pay.tbank.ru/2cLnq988	CONFIRMED	aleksandr.antipov.1998@hotmail.com
19	29	1546647171	1m	31	paid	500	8466789666	2026-05-08 14:15:46.253833+00	2026-05-08 14:18:38.825324+00	0	\N	23	buy	1546647171-1	2204	https://pay.tbank.ru/FNr8StW5	CONFIRMED	lena2505098@mail.ru
18	29	1546647171	1m	31	pending_payment	500	8466339977	2026-05-08 12:50:14.520598+00	\N	2	2026-05-08 17:00:08.459056+00	22	buy	1546647171	1053	https://pay.tbank.ru/eb2oS0EW	NEW	lena2505098@mail.ru
14	7	1174725369	1m	31	paid	500	8446992637	2026-05-05 08:31:02.951366+00	2026-05-05 08:31:50.41699+00	0	\N	12	buy	1174725369-2	6487	https://pay.tbank.ru/ZGnMCBg2	CONFIRMED	yelena.krilowa@yandex.ru
2	3	884782147	1m	31	paid	500	8444966982	2026-05-05 00:12:16.116452+00	2026-05-05 09:17:24.289892+00	2	2026-05-05 04:15:08.015751+00	3	buy	884782147	3438	https://pay.tbank.ru/Wq8eqP8b	CONFIRMED	\N
7	7	1174725369	1m	31	created	500	\N	2026-05-05 06:58:07.602721+00	\N	2	2026-05-05 11:30:09.05184+00	10	buy	1174725369	6555	\N	\N	\N
8	7	1174725369	1m	31	created	500	\N	2026-05-05 06:59:38.185599+00	\N	2	2026-05-05 11:30:09.05184+00	11	buy	1174725369-1	2099	\N	\N	\N
9	1	795564969	1m	31	created	500	\N	2026-05-05 07:30:13.74675+00	\N	2	2026-05-05 11:45:09.334485+00	1	renew	795564969	9649	\N	\N	\N
10	1	795564969	1m	31	created	500	\N	2026-05-05 07:31:30.420595+00	\N	2	2026-05-05 11:45:09.334485+00	1	renew	795564969	2580	\N	\N	\N
11	1	795564969	1m	31	created	500	\N	2026-05-05 07:32:54.513827+00	\N	2	2026-05-05 11:45:09.334485+00	1	renew	795564969	1414	\N	\N	\N
15	8	1055039542	1m	31	pending_payment	500	8447039171	2026-05-05 08:39:16.212849+00	\N	2	2026-05-05 12:45:08.448907+00	13	buy	1055039542	4204	https://pay.tbank.ru/C7VeNOnh	NEW	skopintsev.a@yandex.ru
\.


--
-- Data for Name: referrals; Type: TABLE DATA; Schema: public; Owner: telegrambot
--

COPY public.referrals (id, referrer_telegram_id, referred_telegram_id, status, reward_days, created_at, rewarded_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: telegrambot
--

COPY public.users (id, telegram_id, username, created_at, first_name, is_active, subscription_until) FROM stdin;
1	795564969	admMik	2026-05-04 23:02:48.235449	Генерал Урал	t	\N
2	2041577539	\N	2026-05-04 23:45:01.817239	Коржик	t	\N
3	884782147	CopSPb	2026-05-05 00:06:55.727822	Шерлок	t	\N
4	6005708286	Mastak16	2026-05-05 04:44:02.919939	Мастак	t	\N
5	5838788351	xawa8	2026-05-05 06:08:58.555866	ᛏxawaᛉ	t	\N
6	5967788433	\N	2026-05-05 06:15:45.360564	Монах	t	\N
7	1174725369	Alena293015	2026-05-05 06:57:06.806499	алена	t	\N
8	1055039542	Smolanas	2026-05-05 08:38:43.544626	Анастасия	t	\N
9	6921488217	\N	2026-05-05 08:47:31.279746	Макс	t	\N
10	5764072432	\N	2026-05-05 08:56:46.247109	Lake	t	\N
11	5722389050	ALMAZ98rus	2026-05-05 12:13:15.182734	АЛМАZ	t	\N
12	7232869705	Servicccccc	2026-05-05 12:40:28.334237	Servik	t	\N
13	473190992	Gravy_Fox	2026-05-05 13:58:55.676907	Alex	t	\N
14	5964583875	Miron22091810	2026-05-05 14:18:28.785538	Евгений	t	\N
15	1701296410	Shubin_tamam	2026-05-05 14:51:29.335982	Viktor K (Шубин)	t	\N
16	1929095264	\N	2026-05-05 16:05:26.222139	Кречет	t	\N
17	1192348857	Aleksej68tmb	2026-05-05 17:18:19.412333	Алексей	t	\N
18	5216776182	Sergei_sergeevi4	2026-05-06 04:24:31.280425	МОЩНЫЙ 🇷🇺	t	\N
19	1056461560	Bnd23	2026-05-06 10:23:05.939919	Фокс	t	\N
20	7791390441	in_astral	2026-05-06 10:49:20.9339	𝙾𝚢𝚊𝚜𝚞𝚖𝚒	t	\N
21	5068088981	Skiff1n	2026-05-06 11:31:12.725635	Skoff1n	t	\N
22	2142042154	\N	2026-05-06 20:42:15.817303	K	t	\N
23	136973392	burn1ng_chr0m3	2026-05-06 20:44:39.059743	Wayland	t	\N
24	5384294486	Mayachok43	2026-05-06 20:49:29.358448	Дмитрий	t	\N
25	5840282463	Jekas479	2026-05-07 11:49:09.933643	Евгений	t	\N
26	1058542054	Niket1198	2026-05-07 13:08:29.287556	Nik	t	\N
27	1062543299	ildin98	2026-05-07 13:29:53.866157	Хан	t	\N
28	5620912112	\N	2026-05-08 11:49:33.664221	Константин	t	\N
29	1546647171	ElenaRazum	2026-05-08 12:47:41.416731	Елена	t	\N
30	8156881768	mayak10	2026-05-09 18:22:55.720465	Маяк	t	\N
31	623688898	shmykovmaks	2026-05-10 15:57:51.927071	Максим	t	\N
32	1402395109	ivanivanovih333	2026-05-11 06:04:22.969744	Ivan	t	\N
33	6416437178	Chermo999	2026-05-11 15:24:40.785781	Чермо	t	\N
\.


--
-- Data for Name: vpn_subscriptions; Type: TABLE DATA; Schema: public; Owner: telegrambot
--

COPY public.vpn_subscriptions (id, user_id, telegram_id, cer_id, cert_path, status, created_at, paid_at, expires_at, tariff_code, identity_enabled, cert_created_at, cert_expires_at, reminded_7d, reminded_3d, reminded_1d, cert_sent_at) FROM stdin;
1	1	795564969	795564969	./storage/certs/795564969.p12	sent	2026-05-04 23:24:53.787807+00	2026-05-04 23:25:50.161849+00	2026-06-04 23:25:50.161849+00	1m	t	2026-05-04 23:25:12.466257+00	2027-05-11 23:24:53.786495+00	f	f	f	2026-05-04 23:25:50.288785+00
19	14	5964583875	5964583875	./storage/certs/5964583875.p12	paid	2026-05-05 14:20:34.415532+00	2026-05-05 14:20:39.008835+00	2027-05-12 14:20:39.008835+00	12m	t	2026-05-05 14:20:38.995708+00	2027-05-12 14:20:34.379263+00	f	f	f	\N
2	2	2041577539	2041577539	./storage/certs/2041577539.p12	paid	2026-05-04 23:51:10.757418+00	2026-05-04 23:51:25.387593+00	2027-05-11 23:51:25.387593+00	12m	t	2026-05-04 23:51:25.382031+00	2027-05-11 23:51:10.755878+00	f	f	f	\N
4	3	884782147	884782147-1	./storage/certs/884782147-1.p12	paid	2026-05-05 01:22:32.039433+00	2026-05-05 01:22:51.698702+00	2026-06-05 01:22:51.698702+00	1m	t	2026-05-05 01:22:51.692804+00	2027-05-12 01:22:32.037559+00	f	f	f	\N
20	19	1056461560	1056461560	./storage/certs/1056461560.p12	sent	2026-05-06 10:25:32.567048+00	2026-05-06 10:29:54.873828+00	2026-06-06 10:29:54.873828+00	1m	t	2026-05-06 10:25:46.368586+00	2027-05-13 10:25:32.565243+00	f	f	f	2026-05-06 10:29:55.023202+00
21	28	5620912112	5620912112	./storage/certs/5620912112.p12	sent	2026-05-08 12:01:12.124002+00	2026-05-08 12:01:57.17612+00	2026-06-08 12:01:57.17612+00	1m	t	2026-05-08 12:01:21.805143+00	2027-05-15 12:01:12.121917+00	f	f	f	2026-05-08 12:01:57.38743+00
9	4	6005708286	6005708286	./storage/certs/6005708286.p12	paid	2026-05-05 04:49:40.621465+00	2026-05-05 04:49:49.182202+00	2027-05-12 04:49:49.182202+00	12m	t	2026-05-05 04:49:49.174866+00	2027-05-12 04:49:40.61973+00	f	f	f	\N
10	7	1174725369	1174725369	./storage/certs/1174725369.p12	cert_created	2026-05-05 06:58:07.575263+00	\N	\N	\N	f	2026-05-05 06:58:33.361347+00	2027-05-12 06:58:07.572734+00	f	f	f	\N
11	7	1174725369	1174725369-1	./storage/certs/1174725369-1.p12	cert_created	2026-05-05 06:59:38.179141+00	\N	\N	\N	f	2026-05-05 06:59:59.773915+00	2027-05-12 06:59:38.178853+00	f	f	f	\N
22	29	1546647171	1546647171	./storage/certs/1546647171.p12	cert_created	2026-05-08 12:50:14.515716+00	\N	\N	\N	f	2026-05-08 12:50:31.261879+00	2027-05-15 12:50:14.515323+00	f	f	f	\N
12	7	1174725369	1174725369-2	./storage/certs/1174725369-2.p12	sent	2026-05-05 08:31:02.939062+00	2026-05-05 08:31:50.425747+00	2026-06-05 08:31:50.425747+00	1m	t	2026-05-05 08:31:08.606417+00	2027-05-12 08:31:02.937132+00	f	f	f	2026-05-05 08:31:50.57527+00
13	8	1055039542	1055039542	./storage/certs/1055039542.p12	cert_created	2026-05-05 08:39:16.206093+00	\N	\N	\N	f	2026-05-05 08:39:35.846446+00	2027-05-12 08:39:16.205675+00	f	f	f	\N
14	6	5967788433	5967788433	./storage/certs/5967788433.p12	paid	2026-05-05 08:56:00.352862+00	2026-05-05 08:56:21.039129+00	2027-05-12 08:56:21.039129+00	12m	t	2026-05-05 08:56:21.030172+00	2027-05-12 08:56:00.35055+00	f	f	f	\N
15	10	5764072432	5764072432	\N	pending_payment	2026-05-05 08:56:46.26453+00	\N	\N	\N	f	\N	2027-05-12 08:56:46.263012+00	f	f	f	\N
16	10	5764072432	5764072432-1	\N	pending_payment	2026-05-05 09:00:33.822812+00	\N	\N	\N	f	\N	2027-05-12 09:00:33.820384+00	f	f	f	\N
17	10	5764072432	5764072432-2	./storage/certs/5764072432-2.p12	paid	2026-05-05 09:10:56.138717+00	2026-05-05 09:11:05.791396+00	2027-05-12 09:11:05.791396+00	12m	t	2026-05-05 09:11:05.784366+00	2027-05-12 09:10:56.1366+00	f	f	f	\N
23	29	1546647171	1546647171-1	./storage/certs/1546647171-1.p12	sent	2026-05-08 14:15:46.247911+00	2026-05-08 14:18:38.83034+00	2026-06-08 14:18:38.83034+00	1m	t	2026-05-08 14:16:23.987311+00	2027-05-15 14:15:46.24755+00	f	f	f	2026-05-08 14:18:38.961502+00
3	3	884782147	884782147	./storage/certs/884782147.p12	sent	2026-05-05 00:12:16.107869+00	2026-05-05 09:17:24.294791+00	2026-06-05 09:17:24.294791+00	1m	t	2026-05-05 00:13:03.810428+00	2027-05-12 00:12:16.106693+00	f	f	f	2026-05-05 09:17:24.432213+00
18	11	5722389050	5722389050	./storage/certs/5722389050.p12	paid	2026-05-05 12:14:16.116737+00	2026-05-05 12:14:28.762832+00	2027-05-12 12:14:28.762832+00	12m	t	2026-05-05 12:14:28.756527+00	2027-05-12 12:14:16.11402+00	f	f	f	\N
\.


--
-- Name: certificates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: telegrambot
--

SELECT pg_catalog.setval('public.certificates_id_seq', 1, false);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: telegrambot
--

SELECT pg_catalog.setval('public.orders_id_seq', 19, true);


--
-- Name: referrals_id_seq; Type: SEQUENCE SET; Schema: public; Owner: telegrambot
--

SELECT pg_catalog.setval('public.referrals_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: telegrambot
--

SELECT pg_catalog.setval('public.users_id_seq', 33, true);


--
-- Name: vpn_subscriptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: telegrambot
--

SELECT pg_catalog.setval('public.vpn_subscriptions_id_seq', 23, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: certificates certificates_pkey; Type: CONSTRAINT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: orders orders_public_order_id_key; Type: CONSTRAINT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_public_order_id_key UNIQUE (public_order_id);


--
-- Name: referrals referrals_pkey; Type: CONSTRAINT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.referrals
    ADD CONSTRAINT referrals_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: vpn_subscriptions vpn_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.vpn_subscriptions
    ADD CONSTRAINT vpn_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: ix_certificates_cert_id; Type: INDEX; Schema: public; Owner: telegrambot
--

CREATE UNIQUE INDEX ix_certificates_cert_id ON public.certificates USING btree (cert_id);


--
-- Name: ix_orders_telegram_id; Type: INDEX; Schema: public; Owner: telegrambot
--

CREATE INDEX ix_orders_telegram_id ON public.orders USING btree (telegram_id);


--
-- Name: ix_orders_user_id; Type: INDEX; Schema: public; Owner: telegrambot
--

CREATE INDEX ix_orders_user_id ON public.orders USING btree (user_id);


--
-- Name: ix_referrals_referred_telegram_id; Type: INDEX; Schema: public; Owner: telegrambot
--

CREATE UNIQUE INDEX ix_referrals_referred_telegram_id ON public.referrals USING btree (referred_telegram_id);


--
-- Name: ix_referrals_referrer_telegram_id; Type: INDEX; Schema: public; Owner: telegrambot
--

CREATE INDEX ix_referrals_referrer_telegram_id ON public.referrals USING btree (referrer_telegram_id);


--
-- Name: ix_users_telegram_id; Type: INDEX; Schema: public; Owner: telegrambot
--

CREATE UNIQUE INDEX ix_users_telegram_id ON public.users USING btree (telegram_id);


--
-- Name: ix_vpn_subscriptions_cer_id; Type: INDEX; Schema: public; Owner: telegrambot
--

CREATE UNIQUE INDEX ix_vpn_subscriptions_cer_id ON public.vpn_subscriptions USING btree (cer_id);


--
-- Name: ix_vpn_subscriptions_telegram_id; Type: INDEX; Schema: public; Owner: telegrambot
--

CREATE INDEX ix_vpn_subscriptions_telegram_id ON public.vpn_subscriptions USING btree (telegram_id);


--
-- Name: ix_vpn_subscriptions_user_id; Type: INDEX; Schema: public; Owner: telegrambot
--

CREATE INDEX ix_vpn_subscriptions_user_id ON public.vpn_subscriptions USING btree (user_id);


--
-- Name: certificates certificates_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: telegrambot
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 23uAQFNJexqZEXC8dRP2jhxIsJFjHd5u3Eeh3n7TWuoLYXTtC2OBE9XIcTHJ8rG

