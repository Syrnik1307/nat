module.exports = function override(config, env) {
  // Исправление для allowedHosts
  if (config.devServer) {
    config.devServer.allowedHosts = 'all';
  }
  return config;
};
