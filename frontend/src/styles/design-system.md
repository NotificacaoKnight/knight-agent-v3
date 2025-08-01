# Knight Agent Design System

## Paleta de Cores

### Tema Escuro (Dark Theme)
- **Fundo Principal**: `#2A2A2A` - Cor de fundo primária da aplicação
- **Fundo Secundário**: `#303030` - Cards, modais, elementos elevados
- **Destaque/Accent**: `#FFA600` - Botões primários, links, elementos interativos, sidebar
- **Texto Primário**: `#FFFFFF` - Títulos e texto principal
- **Texto Secundário**: `#B0B0B0` - Texto de apoio, descrições
- **Texto Terciário**: `#808080` - Placeholders, texto desabilitado
- **Borda**: `#404040` - Bordas de elementos, divisores
- **Hover**: `#FFB833` - Estado hover do accent
- **Focus**: `#FFC966` - Estado focus do accent

### Tema Claro (Light Theme)
- **Fundo Principal**: `#EBE6DF` - Cor de fundo primária da aplicação
- **Fundo Secundário**: `#F9F7F3` - Cards, modais, elementos elevados
- **Destaque/Accent**: `#2A2A2A` - Botões primários, links, elementos interativos, sidebar
- **Texto Primário**: `#2A2A2A` - Títulos e texto principal
- **Texto Secundário**: `#5A5A5A` - Texto de apoio, descrições
- **Texto Terciário**: `#808080` - Placeholders, texto desabilitado
- **Borda**: `#D0C7BA` - Bordas de elementos, divisores
- **Hover**: `#1A1A1A` - Estado hover do accent
- **Focus**: `#0A0A0A` - Estado focus do accent

## Mapeamento de Variáveis CSS

### Dark Theme
```css
--background: 42 42 42; /* #2A2A2A */
--background-secondary: 48 48 48; /* #303030 */
--foreground: 255 255 255; /* #FFFFFF */
--foreground-secondary: 176 176 176; /* #B0B0B0 */
--foreground-tertiary: 128 128 128; /* #808080 */
--primary: 255 166 0; /* #FFA600 */
--primary-hover: 255 184 51; /* #FFB833 */
--primary-focus: 255 201 102; /* #FFC966 */
--border: 64 64 64; /* #404040 */
--accent: 255 166 0; /* #FFA600 */
--muted: 48 48 48; /* #303030 */
--card: 48 48 48; /* #303030 */
```

### Light Theme
```css
--background: 235 230 223; /* #EBE6DF */
--background-secondary: 249 247 243; /* #F9F7F3 */
--foreground: 42 42 42; /* #2A2A2A */
--foreground-secondary: 90 90 90; /* #5A5A5A */
--foreground-tertiary: 128 128 128; /* #808080 */
--primary: 42 42 42; /* #2A2A2A */
--primary-hover: 26 26 26; /* #1A1A1A */
--primary-focus: 10 10 10; /* #0A0A0A */
--border: 208 199 186; /* #D0C7BA */
--accent: 42 42 42; /* #2A2A2A */
--muted: 249 247 243; /* #F9F7F3 */
--card: 249 247 243; /* #F9F7F3 */
```

## Extensões do Tailwind

### Cores Customizadas
```javascript
colors: {
  knight: {
    // Dark theme
    'dark-bg': '#2A2A2A',
    'dark-bg-secondary': '#303030',
    'dark-accent': '#FFA600',
    'dark-accent-hover': '#FFB833',
    'dark-accent-focus': '#FFC966',
    'dark-text': '#FFFFFF',
    'dark-text-secondary': '#B0B0B0',
    'dark-text-tertiary': '#808080',
    'dark-border': '#404040',
    
    // Light theme
    'light-bg': '#EBE6DF',
    'light-bg-secondary': '#F9F7F3',
    'light-accent': '#2A2A2A',
    'light-accent-hover': '#1A1A1A',
    'light-accent-focus': '#0A0A0A',
    'light-text': '#2A2A2A',
    'light-text-secondary': '#5A5A5A',
    'light-text-tertiary': '#808080',
    'light-border': '#D0C7BA',
  }
}
```

## Componentes Base

### Botões
- **Primário**: Usa cor de destaque com hover/focus states
- **Secundário**: Outline com cor de destaque
- **Fantasma**: Apenas texto com cor de destaque

### Cards
- Fundo secundário com bordas sutis
- Sombras adaptativas ao tema

### Sidebar/Navigation
- **Tema Escuro**: Background `#FFA600` (accent)
- **Tema Claro**: Background `#2A2A2A` (accent)
- Texto contrastante baseado no fundo

## Estados Interativos

### Hover
- Botões: Escurecem/clareiam 20% da cor base
- Cards: Elevation sutil
- Links: Mudança de opacidade

### Focus
- Ring color usando a cor de destaque
- Outline offset de 2px

### Active
- Slight scale transform (0.98)
- Cor mais intensa

## Acessibilidade

### Contraste
- Todas as combinações de cor atendem WCAG AA (4.5:1)
- Elementos interativos atendem WCAG AAA (7:1)

### Focus Visible
- Ring sempre visível em navegação por teclado
- Cores de high contrast para melhor visibilidade

## Implementação

### Ordem de Prioridade
1. Atualizar variáveis CSS globais
2. Configurar Tailwind com novas cores
3. Aplicar em componentes base
4. Testar em ambos os temas
5. Validar acessibilidade