import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 20000,
});

export async function predictLive({ latitude, longitude, cityName, alertEmail }) {
  const body = cityName
    ? { city_name: cityName, alert_email: alertEmail }
    : { latitude, longitude, alert_email: alertEmail };
  const { data } = await client.post("/predict/live", body);
  return data;
}

export async function predictManual(featureInput) {
  const { data } = await client.post("/predict", featureInput);
  return data;
}

export async function getRecentPredictions(limit = 50) {
  const { data } = await client.get(`/predictions/recent?limit=${limit}`);
  return data;
}

export async function getMapPredictions() {
  const { data } = await client.get("/predictions/map");
  return data;
}

export async function getModelComparison() {
  const { data } = await client.get("/models/compare");
  return data;
}

export async function getRecentAlerts(limit = 20) {
  const { data } = await client.get(`/alerts/recent?limit=${limit}`);
  return data;
}

export function extractErrorMessage(error) {
  return (
    error?.response?.data?.error ||
    error?.message ||
    "Something went wrong talking to the prediction service."
  );
}

export default client;
