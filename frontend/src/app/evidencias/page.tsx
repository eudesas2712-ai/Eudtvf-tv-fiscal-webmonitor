import AppShell from "../../components/AppShell";
import EvidenceConsole from "../../components/EvidenceConsole";

export default function EvidenciasPage() {
  return (
    <AppShell
      title="Evidências operacionais"
      subtitle="Checking publicitário, inteligência de mercado e candidatos a notícia em uma única tela filtrável."
    >
      <EvidenceConsole />
    </AppShell>
  );
}
