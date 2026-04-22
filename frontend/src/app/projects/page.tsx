"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type ProjectOption = {
  project_id: string;
  label: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const PROJECT_OPTIONS_URL = `${API_BASE}/projects/projects/intel-options/`;

function normalizeProjectLabel(option: ProjectOption) {
  return option.label || option.project_id || "Projeto sem identificação";
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadProjects() {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(PROJECT_OPTIONS_URL, {
          method: "GET",
          cache: "no-store",
          headers: {
            accept: "application/json",
          },
        });

        if (!response.ok) {
          throw new Error(`Falha ao carregar projetos (${response.status})`);
        }

        const json = await response.json();

        if (active) {
          setProjects(Array.isArray(json) ? json : []);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Erro ao carregar a lista de projetos."
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadProjects();

    return () => {
      active = false;
    };
  }, []);

  const totalProjects = useMemo(() => projects.length, [projects]);

  return (
    <main className="projects-page">
      <div className="projects-container">
        <section className="hero">
          <div className="hero-brand">
            <div className="hero-logo-frame">
              <img
                src="/logo-tv-fiscal-clean.png"
                alt="TV Fiscal"
                className="hero-logo"
              />
            </div>

            <div>
              <div className="eyebrow">TV Fiscal WebMonitor</div>
              <h1>Projetos monitorados</h1>
              <p>
                Entrada principal do módulo publicitário para acesso aos painéis
                de inteligência por projeto.
              </p>
            </div>
          </div>

          <div className="hero-summary">
            <div className="summary-label">Total de projetos</div>
            <div className="summary-value">{totalProjects}</div>
          </div>
        </section>

        {loading && (
          <div className="info-box">Carregando lista de projetos...</div>
        )}

        {!loading && error && <div className="error-box">{error}</div>}

        {!loading && !error && projects.length === 0 && (
          <div className="info-box">
            Nenhum projeto disponível para monitoramento.
          </div>
        )}

        {!loading && !error && projects.length > 0 && (
          <section className="projects-grid">
            {projects.map((project) => {
              const projectLabel = normalizeProjectLabel(project);
              const intelUrl = `/intel?project_id=${encodeURIComponent(
                project.project_id
              )}`;

              return (
                <article key={project.project_id} className="project-card">
                  <div className="project-top">
                    <div className="project-badge">Projeto</div>
                    <h2>{projectLabel}</h2>
                  </div>

                  <div className="project-meta">
                    <div className="meta-label">Project ID</div>
                    <div className="meta-value">{project.project_id}</div>
                  </div>

                  <div className="project-actions">
                    <Link href={intelUrl} className="primary-btn">
                      Abrir Intel
                    </Link>

                    <a
                      href={`${API_BASE}/intel/report/pdf/${project.project_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="secondary-btn"
                    >
                      PDF
                    </a>

                    <a
                      href={`${API_BASE}/intel/report/pptx/${project.project_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="secondary-btn"
                    >
                      PPTX
                    </a>
                  </div>
                </article>
              );
            })}
          </section>
        )}
      </div>

      <style jsx>{`
        .projects-page {
          min-height: 100vh;
          background: #f6f7fb;
          color: #1f2937;
        }

        .projects-container {
          max-width: 1280px;
          margin: 0 auto;
          padding: 24px;
        }

        .hero {
          display: flex;
          justify-content: space-between;
          gap: 24px;
          align-items: center;
          background: linear-gradient(135deg, #7a1118 0%, #b91c1c 45%, #d93636 100%);
          color: #fff;
          border-radius: 28px;
          padding: 32px;
          box-shadow: 0 10px 30px rgba(153, 27, 27, 0.18);
          margin-bottom: 24px;
        }

        .hero-brand {
          display: flex;
          align-items: center;
          gap: 18px;
        }

        .hero-logo-frame {
          width: 86px;
          height: 86px;
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.1);
          padding: 6px;
          box-sizing: border-box;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .hero-logo {
          width: 100%;
          height: 100%;
          object-fit: contain;
          object-position: center;
          display: block;
        }

        .eyebrow {
          font-size: 12px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          font-weight: 700;
          opacity: 0.9;
          margin-bottom: 10px;
        }

        h1 {
          font-size: 42px;
          line-height: 1.05;
          margin: 0;
          font-weight: 800;
        }

        .hero p {
          margin: 12px 0 0;
          font-size: 17px;
          max-width: 760px;
          color: rgba(255, 255, 255, 0.92);
        }

        .hero-summary {
          min-width: 180px;
          background: rgba(255, 255, 255, 0.14);
          border-radius: 18px;
          padding: 18px 20px;
          backdrop-filter: blur(6px);
        }

        .summary-label {
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.12em;
          color: rgba(255, 255, 255, 0.82);
        }

        .summary-value {
          margin-top: 8px;
          font-size: 34px;
          font-weight: 800;
        }

        .info-box,
        .error-box {
          border-radius: 18px;
          padding: 18px 20px;
          margin-bottom: 20px;
          background: #fff;
          border: 1px solid #e5e7eb;
        }

        .error-box {
          background: #fef2f2;
          border-color: #fecaca;
          color: #b91c1c;
        }

        .projects-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 16px;
        }

        .project-card {
          background: #fff;
          border: 1px solid #e8e8ee;
          border-radius: 22px;
          padding: 22px;
          box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
          display: flex;
          flex-direction: column;
          gap: 18px;
        }

        .project-top h2 {
          margin: 8px 0 0;
          font-size: 22px;
          line-height: 1.25;
          color: #111827;
        }

        .project-badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 6px 10px;
          border-radius: 999px;
          background: #fef2f2;
          color: #b91c1c;
          border: 1px solid #fecaca;
          font-size: 12px;
          font-weight: 700;
          width: fit-content;
        }

        .project-meta {
          padding: 14px 16px;
          border: 1px solid #eef0f4;
          border-radius: 16px;
          background: #f9fafb;
        }

        .meta-label {
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: #6b7280;
        }

        .meta-value {
          margin-top: 8px;
          font-size: 14px;
          line-height: 1.5;
          color: #111827;
          word-break: break-all;
          font-weight: 600;
        }

        .project-actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }

        .primary-btn,
        .secondary-btn {
          border: 0;
          font-weight: 700;
          font-size: 14px;
          border-radius: 14px;
          padding: 12px 16px;
          cursor: pointer;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          justify-content: center;
        }

        .primary-btn {
          background: #b91c1c;
          color: #fff;
          box-shadow: 0 8px 20px rgba(185, 28, 28, 0.18);
        }

        .secondary-btn {
          background: #ffffff;
          color: #991b1b;
          border: 1px solid #e5e7eb;
        }

        @media (max-width: 1100px) {
          .projects-grid {
            grid-template-columns: 1fr 1fr;
          }

          .hero {
            flex-direction: column;
            align-items: flex-start;
          }

          .hero-summary {
            min-width: 0;
            width: 100%;
          }
        }

        @media (max-width: 760px) {
          .projects-container {
            padding: 16px;
          }

          .projects-grid {
            grid-template-columns: 1fr;
          }

          .hero-brand {
            align-items: flex-start;
          }

          h1 {
            font-size: 34px;
          }

          .hero p {
            font-size: 15px;
          }
        }
      `}</style>
    </main>
  );
}