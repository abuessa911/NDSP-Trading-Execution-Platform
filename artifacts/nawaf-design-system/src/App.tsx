import { DesignSystemBrowser } from "./preview/DesignSystemBrowser";
import { ReviewProvider } from "./preview/i18n";

function App() {
  return (
    <ReviewProvider>
      <DesignSystemBrowser />
    </ReviewProvider>
  );
}

export default App;
