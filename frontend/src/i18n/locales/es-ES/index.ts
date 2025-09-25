/**
 * Spanish (Spain) translations - Fallback resources
 */

const common = {
  // App
  app_name: 'Knight Agent',
  app_description: 'Asistente de IA Corporativo',
  
  // Common actions
  welcome: 'Bienvenido',
  hello: 'Hola',
  goodbye: 'Adiós',
  yes: 'Sí',
  no: 'No',
  save: 'Guardar',
  cancel: 'Cancelar',
  delete: 'Eliminar',
  edit: 'Editar',
  create: 'Crear',
  update: 'Actualizar',
  search: 'Buscar',
  filter: 'Filtrar',
  clear: 'Limpiar',
  reset: 'Reiniciar',
  submit: 'Enviar',
  loading: 'Cargando...',
  success: 'Éxito',
  error: 'Error',
  warning: 'Advertencia',
  info: 'Información',
  confirm: 'Confirmar',
  close: 'Cerrar',
  open: 'Abrir',
  view: 'Ver',
  download: 'Descargar',
  upload: 'Subir',
  
  // User
  profile: 'Perfil',
  settings: 'Configuración',
  logout: 'Cerrar Sesión',
  login: 'Iniciar Sesión',
  
  // Language
  language: 'Idioma',
  change_language: 'Cambiar Idioma',
  
  // Status
  active: 'Activo',
  inactive: 'Inactivo',
  online: 'En línea',
  offline: 'Sin conexión'
};

const navigation = {
  dashboard: 'Panel de Control',
  chat: 'Chat',
  documents: 'Documentos',
  settings: 'Configuración',
  help: 'Ayuda',
  about: 'Acerca de'
};

const chat = {
  title: 'Chatear con Knight',
  placeholder: 'Escribe tu mensaje...',
  send: 'Enviar',
  new_conversation: 'Nueva Conversación',
  conversation_history: 'Historial de Conversaciones',
  thinking: 'Knight está pensando...',
  error_message: 'Lo siento, encontré un error. Inténtalo de nuevo.',
  welcome_message: '¡Hola! Soy Knight, tu asistente de IA. ¿Cómo puedo ayudarte hoy?',

  // Time-based greetings
  good_morning: 'Buenos días',
  good_afternoon: 'Buenas tardes',
  good_evening: 'Buenas noches',

  // Greeting patterns (using {{firstName}} for interpolation)
  greeting_time_name: '¡{{timeGreeting}}, {{firstName}}!',
  greeting_hello: '¡Hola, {{firstName}}!',
  greeting_hi: '¡Hola, {{firstName}}!',
  greeting_whats_up: '¿Qué tal, {{firstName}}?',
  greeting_whats_new: '¿Qué hay de nuevo, {{firstName}}?',
  greeting_how_help: '¿Cómo puedo ayudar, {{firstName}}?',
  greeting_ready_work: '¿Listo para trabajar, {{firstName}}?',
  greeting_lets_start: '¿Empezamos, {{firstName}}?',
  greeting_time_how_are_you: '¡{{timeGreeting}}! ¿Cómo estás, {{firstName}}?',
  greeting_welcome: '¡Bienvenido, {{firstName}}!',

  // Audio and error messages
  audio_message: 'Mensaje de audio',
  response_with_documents: 'Respuesta basada en documentos corporativos',
  send_error: 'Error al enviar mensaje. Inténtalo de nuevo.',
  processing_error: 'Error en el procesamiento del mensaje',
  transcription_error: 'Error en la transcripción del audio',
  file_too_large: 'Archivo demasiado grande (máx 20MB)',
  unsupported_format: 'Formato de audio no soportado',
  session_load_error: 'Error al cargar historial de la conversación',
  processing_message_error: 'Lo siento, ocurrió un error al procesar tu mensaje. Inténtalo de nuevo.'
};

const documents = {
  title: 'Documentos',
  upload: 'Subir Documento',
  upload_success: 'Documento subido exitosamente',
  upload_error: 'Error al subir documento',
  processing: 'Procesando documento...',
  no_documents: 'No se encontraron documentos',
  search_documents: 'Buscar documentos...'
};

const settings = {
  title: 'Configuración',
  language_preferences: 'Preferencias de Idioma',
  select_language: 'Selecciona tu idioma preferido',
  theme: 'Tema',
  light_theme: 'Claro',
  dark_theme: 'Oscuro',
  system_theme: 'Sistema',
  save_settings: 'Guardar Configuración',
  settings_saved: 'Configuración guardada exitosamente',
  user_profile: 'Perfil de Usuario',
  theme_preferences: 'Preferencias de Tema',
  privacy: 'Privacidad',
  security: 'Seguridad',
  account: 'Cuenta',
  preferences: 'Preferencias del Sistema',
  advanced: 'Configuración Avanzada',

  // Profile section
  photo_synced_microsoft: 'Foto sincronizada de Microsoft 365',
  name: 'Nombre',
  email: 'Email',
  department: 'Departamento',
  job_title: 'Cargo',
  not_informed: 'No informado',

  // Notifications
  notifications: 'Notificaciones',
  notifications_new_messages: 'Notificaciones de nuevos mensajes',
  notifications_documents_processed: 'Notificaciones de documentos procesados',
  notifications_email: 'Notificaciones por email',

  // Appearance
  appearance: 'Apariencia',
  theme_toggle_hint: 'Use el botón de tema en la barra lateral para alternar entre modo claro y oscuro.',

  // AI Settings
  ai_settings: 'Configuración de IA',
  admin_badge: 'Admin',

  // Privacy
  privacy_security: 'Privacidad y Seguridad',
  session: 'Sesión',
  session_expiry_info: 'Su sesión expira automáticamente después de 1 hora de inactividad',
  conversation_history: 'Historial de Conversaciones',
  conversation_storage_info: 'Sus últimas 10 conversaciones se almacenan de forma segura',

  // Admin Management
  admin_management: 'Gestión de Administradores',
  add_new_admin: 'Agregar Nuevo Administrador',
  admin_privilege_info: 'El usuario recibirá privilegios de administrador en el próximo inicio de sesión',
  current_admins: 'Administradores Actuales',
  you_label: '(tú)',
  add_button: 'Agregar',
  remove_admin_confirm: '¿Está seguro de que desea eliminar a {{email}} como administrador?',
  error_loading_admins: 'Error al cargar la lista de administradores',
  error_invalid_email: 'Por favor, ingrese un email válido',
  error_adding_admin: 'Error al agregar administrador',
  error_removing_admin: 'Error al eliminar administrador'
};

const errors = {
  generic_error: 'Ha ocurrido un error',
  network_error: 'Error de red. Verifica tu conexión.',
  server_error: 'Error del servidor. Inténtalo más tarde.',
  not_found: 'Página no encontrada',
  unauthorized: 'No tienes autorización para acceder a esta página',
  validation_error: 'Verifica tu entrada e inténtalo de nuevo'
};

const login = {
  welcome: 'Bienvenido',
  enter_with_microsoft: 'Inicia sesión con tu cuenta Microsoft',
  connecting: 'Conectando...',
  enter: 'Iniciar sesión',
  secure: 'Seguro',
  secure_desc: 'Autenticación Microsoft',
  intelligent: 'Inteligente',
  intelligent_desc: 'Integración con IA',
  secure_environment: 'Entorno Seguro',
  activate_dark_mode: 'Activar modo oscuro',
  activate_light_mode: 'Activar modo claro',
  authentication_error: 'Error de autenticación:',
  check_connection: 'Verifica tu conexión a internet e inténtalo de nuevo.',
  connecting_to_microsoft: 'Conectando a cuenta Microsoft'
};

const dashboard = {
  title: 'Panel de Control',
  subtitle: 'Visión general del sistema',
  new_chat: 'Nuevo Chat',
  chat_with_knight: 'Chatear con Knight',
  documents: 'Documentos',
  manage_knowledge: 'Gestionar conocimiento',
  downloads: 'Descargas',
  temporary_files: 'Archivos temporales'
};

const chatPage = {
  ai_assistant: 'Asistente IA',
  loading_history: 'Cargando historial de conversación...',
  conversation_not_found: 'Conversación no encontrada',
  conversation_not_found_desc: 'Esta conversación puede haber sido eliminada o no tienes acceso a ella.',
  good_morning: 'Buenos días',
  good_afternoon: 'Buenas tardes',
  good_evening: 'Buenas noches',
  hello: 'Hola',
  hi: 'Hola',
  whats_up: 'Qué tal',
  whats_new: 'Qué hay de nuevo',
  how_can_i_help: 'Cómo puedo ayudar',
  ready_to_work: 'Listo para trabajar',
  lets_start: 'Empecemos',
  how_are_you: 'Cómo estás',
  welcome_user: 'Bienvenido',
  user: 'usuario',
  audio_message: 'Mensaje de audio',
  error_loading_content: 'Error al cargar contenido del documento',
  context_based_response: 'Respuesta basada en documentos corporativos',
  processing_error: 'Lo siento, ocurrió un error al procesar tu mensaje. Inténtalo de nuevo.',
  send_message_error: 'Error al enviar mensaje. Inténtalo de nuevo.',
  transcription_error: 'Error en la transcripción del audio',
  file_too_large: 'Archivo demasiado grande (máx 20MB)',
  unsupported_format: 'Formato de audio no soportado',
  type_message_or_record: 'Escribe tu mensaje o graba un audio...',
  add_optional_text: 'Añade texto opcional...',
  microphone_access_error: 'No se pudo acceder al micrófono',
  recording_time: 'Grabando... {{time}}',
  recorded_audio: 'Audio grabado ({{time}})',
  remove: 'Eliminar',
  stop_recording: 'Parar grabación',
  record_audio: 'Grabar audio',
  ai_response_warning: 'Esperando respuesta de la IA... Evita cambiar conversaciones para no perder la respuesta.',
  useful_links: 'Enlaces Útiles',
  available_documents: 'Documentos Disponibles',
  preparing_download: 'Preparando descarga...',
  download_completed: '¡Descarga de {{filename}} completada!',
  download_error: 'Error al descargar el archivo'
};

const documentsPage = {
  title: 'Documentos',
  subtitle: 'Gestión de conocimiento',
  knowledge_base: 'Base de conocimiento',
  knowledge_base_desc: 'Documentos que sirven como fuente de información para Knight Agent',
  useful_links: 'Enlaces Útiles',
  useful_links_desc: 'Enlaces que Knight Agent puede compartir con los empleados cuando se solicite',
  forms_and_docs: 'Formularios y Documentos',
  forms_and_docs_desc: 'Documentos que pueden ser descargados por los empleados (formularios, plantillas, etc.)',
  knowledge_management: 'Gestión de conocimiento',
  admin_area_desc: 'Área administrativa para gestión de la base de conocimiento',
  total_documents: 'Total de documentos',
  processed: 'Procesados',
  processing: 'En procesamiento',
  total_chunks: 'Total chunks',
  pending: 'Pendiente',
  processing_status: 'Procesando',
  processed_status: 'Procesado',
  error_status: 'Error',
  document: 'Documento',
  status: 'Estado',
  popularity: 'Popularidad',
  upload_date: 'Fecha de Subida',
  actions: 'Acciones',
  view_content: 'Ver contenido',
  download: 'Descargar',
  delete: 'Eliminar',
  search_documents: 'Buscar documentos...',
  upload_document: 'Subir Documento',
  no_documents_found: 'No se encontraron documentos',
  error_loading_documents: 'Error al cargar documentos',
  check_auth_permissions: 'Verifica que estés autenticado y tengas permisos de administrador',
  add_link: 'Añadir Enlace',
  no_links_found: 'No se encontraron enlaces',
  error_loading_links: 'Error al cargar enlaces útiles',
  check_connection_try_again: 'Verifica tu conexión e inténtalo de nuevo',
  upload_document_modal: 'Subir Documento',
  file: 'Archivo',
  document_title: 'Título del Documento',
  file_types_supported: 'PDF, Word, Excel, PowerPoint, TXT o Markdown (máx. 50MB)',
  type_document_title: 'Ingresa el título del documento',
  sending: 'Enviando...',
  send: 'Enviar',
  document_sent_processing: 'Documento enviado para procesamiento',
  error_sending_document: 'Error al enviar documento',
  document_deleted_success: 'Documento eliminado exitosamente',
  error_deleting_document: 'Error al eliminar documento',
  confirm_deletion: 'Confirmar Eliminación',
  confirm_delete_document: '¿Estás seguro de que quieres eliminar el documento "{{title}}"? Esta acción no se puede deshacer.',
  deleting: 'Eliminando...',
  markdown_content: 'Contenido en Markdown',
  link: 'Enlace',
  category: 'Categoría',
  sends: 'Envíos',
  created_at: 'Creado el',
  copy_url: 'Copiar URL',
  open_link: 'Abrir enlace',
  url_copied: 'URL copiada al portapapeles',
  edit: 'Editar',
  confirm_delete_link: '¿Estás seguro de que quieres eliminar este enlace?',
  link_created_success: 'Enlace creado exitosamente',
  error_creating_link: 'Error al crear enlace',
  link_updated_success: 'Enlace actualizado exitosamente',
  error_updating_link: 'Error al actualizar enlace',
  link_deleted_success: 'Enlace eliminado exitosamente',
  error_deleting_link: 'Error al eliminar enlace',
  edit_useful_link: 'Editar Enlace Útil',
  add_useful_link: 'Añadir Enlace Útil',
  link_title: 'Título del Enlace',
  link_title_placeholder: 'ej. Portal RRHH - Sistema de Beneficios',
  url: 'URL',
  url_placeholder: 'https://ejemplo.com',
  category_placeholder: 'ej. RRHH, TI, Cumplimiento, Finanzas',
  link_description: 'Descripción del Enlace',
  link_description_placeholder: 'Describe lo que los empleados encontrarán en este enlace...',
  link_description_help: 'Describe el contenido y utilidad del enlace para los empleados',
  ai_guidance: 'Orientación para IA',
  ai_guidance_placeholder: '¿Cuándo debe Knight Agent enviar este enlace? Describe situaciones, palabras clave o contextos...',
  ai_guidance_help: 'Instruye a la IA sobre cuándo compartir este enlace (palabras clave, contextos, situaciones específicas)',
  title_and_url_required: 'Título y URL son obligatorios',
  saving: 'Guardando...',
  update: 'Actualizar',
  downloads_count: 'Descargas',
  download_file: 'Descargar archivo',
  download_started: 'Descarga iniciada',
  confirm_delete_document_modal: '¿Estás seguro de que quieres eliminar este documento?',
  document_created_success: 'Documento creado exitosamente',
  error_creating_document: 'Error al crear documento',
  document_updated_success: 'Documento actualizado exitosamente',
  error_updating_document: 'Error al actualizar documento',
  document_deleted_success_modal: 'Documento eliminado exitosamente',
  error_deleting_document_modal: 'Error al eliminar documento',
  edit_document: 'Editar Documento',
  add_downloadable_document: 'Añadir Documento para Descarga',
  document_title_placeholder: 'ej. Formulario de Solicitud de Vacaciones',
  category_placeholder_docs: 'ej. RRHH, Finanzas, Ventas, Operaciones',
  document_description: 'Descripción del Documento',
  document_description_placeholder: 'Describe lo que este documento contiene y cómo debe usarse...',
  document_description_help: 'Explica el propósito y cómo usar este documento',
  ai_guidance_docs_placeholder: '¿Cuándo debe Knight Agent proporcionar este documento? Describe situaciones, palabras clave o contextos...',
  ai_guidance_docs_help: 'Instruye a la IA sobre cuándo ofrecer este documento (palabras clave, contextos, situaciones específicas)',
  title_and_file_required: 'Título y archivo son obligatorios'
};

const llmManagement = {
  title: 'Gestión de Proveedor LLM',
  subtitle: 'Configuración y monitoreo de proveedores de IA',
  config_tab: 'Configuración',
  metrics_tab: 'Métricas',
  costs_tab: 'Costos',
  history_tab: 'Historial',
  select_provider: 'Seleccionar Proveedor',
  select_provider_placeholder: 'Seleccione un proveedor',
  actions: 'Acciones',
  no_api_key: 'Sin Clave API',
  unavailable: 'No disponible',
  test_provider: 'Probar Proveedor',
  testing: 'Probando...',
  switch_provider: 'Cambiar Proveedor',
  switching: 'Cambiando...',
  provider_status: 'Estado del Proveedor',
  current_provider: 'Proveedor Actual',
  last_test: 'Última Prueba',
  success: 'Éxito',
  failed: 'Falló',
  performance_metrics: 'Métricas de Rendimiento',
  response_time: 'Tiempo de Respuesta',
  success_rate: 'Tasa de Éxito',
  requests_today: 'Solicitudes Hoy',
  total_requests: 'Total de Solicitudes',
  cost_overview: 'Resumen de Costos',
  daily_cost: 'Costo Diario',
  monthly_cost: 'Costo Mensual',
  cost_per_request: 'Costo por Solicitud',
  total_cost: 'Costo Total',
  request_history: 'Historial de Solicitudes',
  recent_requests: 'Solicitudes Recientes',
  no_requests_found: 'No se encontraron solicitudes',
  timestamp: 'Fecha/Hora',
  provider: 'Proveedor',
  tokens: 'Tokens',
  cost: 'Costo',
  status: 'Estado',
  error_loading_data: 'Error al cargar datos',

  // New translations (avoiding duplicates)
  test: 'Probar',
  test_connection: 'Probar Conexión',
  refresh: 'Actualizar',
  available_providers: 'Proveedores Disponibles',
  active: 'Activo',
  online: 'En línea',
  offline: 'Sin conexión',

  // Metrics
  total_queries: 'Total de Consultas',
  avg_response_time: 'Tiempo Promedio',
  estimated_cost: 'Costo Estimado',
  usage_by_provider: 'Uso por Proveedor',
  queries: 'Consultas',
  input_tokens: 'Tokens de Entrada',
  output_tokens: 'Tokens de Salida',

  // Costs
  this_month: 'Este Mes',
  six_months: '6 Meses',
  annual: 'Anual',
  average_per_day: 'Promedio: {{amount}}/día',
  costs_by_period: 'Costos por Período',
  costs_by_provider: 'Costos por Proveedor',
  cost_projections: 'Proyecciones de Costos',
  next_month: 'Próximo Mes',
  next_quarter: 'Próximo Trimestre',
  next_year: 'Próximo Año',
  confidence: 'Confianza',
  not_available: 'No disponible',
  cost_comparison_monthly: 'Comparación de Costos (Mensual)',
  model: 'Modelo',
  input_per_1k: 'Entrada/1k',
  output_per_1k: 'Salida/1k',
  potential_savings: 'Ahorros Potenciales',

  // History
  change_history: 'Historial de Cambios',
  date_time: 'Fecha/Hora',
  user: 'Usuario',
  change: 'Cambio',
  reason: 'Razón',
  no_changes_recorded: 'No se registraron cambios'
};

const deleteModal = {
  delete_conversation: 'Eliminar conversación',
  confirm_delete_conversation: '¿Estás seguro de que quieres eliminar la conversación "{{title}}"?',
  permanent_action_warning: 'Esta acción no se puede deshacer y todos los mensajes serán eliminados permanentemente.',
  deleting: 'Eliminando...',
  delete_conversation_button: 'Eliminar conversación'
};

const sidebar = {
  history: 'Historial',
  information: 'Información',
  recent_documents: 'Documentos Recientes',
  no_documents: 'Ningún documento cargado',
  statistics: 'Estadísticas',
  message_singular: 'mensaje',
  message_plural: 'mensajes'
};

const translations = {
  common,
  navigation,
  chat,
  documents,
  settings,
  errors,
  login,
  dashboard,
  chatPage,
  documentsPage,
  deleteModal,
  llmManagement,
  sidebar
};

export default { translation: translations };