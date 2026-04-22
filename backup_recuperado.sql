--
-- PostgreSQL database dump
--

\restrict ZtIqrIYQ6h5rqSn0EzHMim9iyaUV8by17SuWmk2bp4H1F3qVB2KKw66ij5b4gRZ

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
-- Name: banner_items; Type: TABLE; Schema: public; Owner: webmonitor
--

CREATE TABLE public.banner_items (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    page_url character varying(1024) NOT NULL,
    image_url character varying(2048) NOT NULL,
    alt_text character varying(500),
    width integer,
    height integer,
    normalized_width integer,
    normalized_height integer,
    estimated_value integer,
    pos_x integer,
    pos_y integer,
    source_name character varying(255),
    evidence_html_key character varying(1024),
    evidence_html_url character varying(2048),
    screenshot_page_key character varying(1024),
    screenshot_page_url character varying(2048),
    screenshot_banner_key character varying(1024),
    screenshot_banner_url character varying(2048),
    ocr_text text,
    advertiser_name character varying(255),
    classification character varying(50),
    classification_score integer,
    classification_reason text,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.banner_items OWNER TO webmonitor;

--
-- Name: items; Type: TABLE; Schema: public; Owner: webmonitor
--

CREATE TABLE public.items (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    source_id uuid NOT NULL,
    title character varying(500) NOT NULL,
    url character varying(1024) NOT NULL,
    content_text text NOT NULL,
    matched_terms jsonb NOT NULL,
    evidence_html_key character varying(1024),
    evidence_html_url character varying(2048),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.items OWNER TO webmonitor;

--
-- Name: projects; Type: TABLE; Schema: public; Owner: webmonitor
--

CREATE TABLE public.projects (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.projects OWNER TO webmonitor;

--
-- Name: sources; Type: TABLE; Schema: public; Owner: webmonitor
--

CREATE TABLE public.sources (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    base_url character varying(1024) NOT NULL,
    rss_url character varying(1024),
    enabled boolean NOT NULL,
    interval_minutes integer NOT NULL
);


ALTER TABLE public.sources OWNER TO webmonitor;

--
-- Name: watch_terms; Type: TABLE; Schema: public; Owner: webmonitor
--

CREATE TABLE public.watch_terms (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    term character varying(255) NOT NULL,
    active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.watch_terms OWNER TO webmonitor;

--
-- Data for Name: banner_items; Type: TABLE DATA; Schema: public; Owner: webmonitor
--

COPY public.banner_items (id, project_id, page_url, image_url, alt_text, width, height, normalized_width, normalized_height, estimated_value, pos_x, pos_y, source_name, evidence_html_key, evidence_html_url, screenshot_page_key, screenshot_page_url, screenshot_banner_key, screenshot_banner_url, ocr_text, advertiser_name, classification, classification_score, classification_reason, created_at) FROM stdin;
\.


--
-- Data for Name: items; Type: TABLE DATA; Schema: public; Owner: webmonitor
--

COPY public.items (id, project_id, source_id, title, url, content_text, matched_terms, evidence_html_key, evidence_html_url, created_at) FROM stdin;
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: webmonitor
--

COPY public.projects (id, name, description, created_at) FROM stdin;
\.


--
-- Data for Name: sources; Type: TABLE DATA; Schema: public; Owner: webmonitor
--

COPY public.sources (id, project_id, name, base_url, rss_url, enabled, interval_minutes) FROM stdin;
\.


--
-- Data for Name: watch_terms; Type: TABLE DATA; Schema: public; Owner: webmonitor
--

COPY public.watch_terms (id, project_id, term, active, created_at) FROM stdin;
\.


--
-- Name: banner_items banner_items_pkey; Type: CONSTRAINT; Schema: public; Owner: webmonitor
--

ALTER TABLE ONLY public.banner_items
    ADD CONSTRAINT banner_items_pkey PRIMARY KEY (id);


--
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: webmonitor
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: webmonitor
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: public; Owner: webmonitor
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (id);


--
-- Name: watch_terms watch_terms_pkey; Type: CONSTRAINT; Schema: public; Owner: webmonitor
--

ALTER TABLE ONLY public.watch_terms
    ADD CONSTRAINT watch_terms_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict ZtIqrIYQ6h5rqSn0EzHMim9iyaUV8by17SuWmk2bp4H1F3qVB2KKw66ij5b4gRZ

