const highlights = [
  {
    title: "Analyse narrative",
    description:
      "Transformez vos corpus en scènes, acteurs et événements avec un pipeline entièrement local.",
  },
  {
    title: "Exploration visuelle",
    description:
      "Basculez entre graphes, cartes et synthèses en gardant un contrôle total sur vos données.",
  },
  {
    title: "Expérience sobre",
    description:
      "Une interface moderne, claire et en mode sombre pour rester concentré sur l’essentiel.",
  },
];

export default function App() {
  return (
    <div className="app">
      <header className="hero">
        <span className="badge">VIDOCQ</span>
        <h1>Exploration narrative de corpus</h1>
        <p>
          Une interface React épurée et locale pour analyser des textes en toute
          confidentialité.
        </p>
        <div className="actions">
          <button className="primary">Importer un corpus</button>
          <button className="secondary">Voir les démos</button>
        </div>
      </header>

      <section className="panel">
        <h2>Votre espace de travail</h2>
        <p>
          Prochaine étape : connecter cette interface à l’API locale pour
          déclencher l’extraction, la cartographie et les visualisations.
        </p>
        <div className="grid">
          {highlights.map((item) => (
            <article key={item.title} className="card">
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
