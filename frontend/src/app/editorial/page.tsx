import AppShell from "../../components/AppShell";
import EditorialConsole from "../../components/EditorialConsole";

export default function EditorialPage() {
  return (
    <AppShell
      title="Monitoramento editorial"
      subtitle="Notícias, menções, clipping eletrônico, termos monitorados, sentimento e temas por projeto."
    >
      <EditorialConsole />
    </AppShell>
  );
}
