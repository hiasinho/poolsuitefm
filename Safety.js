.pragma library

// Mirror scripts/player.py's producer-side limits and URL policies.
var textLimit = 256
var tooltipLimit = 512
var urlLimit = 2048
var outputLimit = 16 * 1024
var timeLimit = 7 * 24 * 60 * 60

function parseObject(text) {
  if (typeof text !== "string" || text.length > outputLimit) return null
  try {
    var value = JSON.parse(text)
    return value !== null && typeof value === "object" && !Array.isArray(value) ? value : null
  } catch (error) {
    return null
  }
}

function displayText(value, limit) {
  if (typeof value !== "string") return ""
  return value.slice(0, limit === undefined ? textLimit : limit)
    .replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029]/g, " ")
    .replace(/[\u00ad\u061c\u06dd\u070f\u0890\u0891\u08e2\u180e\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb]/g, "")
    .replace(/[\ud800-\udbff][\udc00-\udfff]|[\ud800-\udfff]/g, function(pair) { return pair.length === 2 ? pair : "" })
    .replace(/\s+/g, " ").trim()
}

function tooltip(value) {
  // The shell owns the tooltip Text. Do not depend on its textFormat setting:
  // lookalikes keep tags/entities inert without double-escaping plain text.
  return displayText(value, tooltipLimit)
    .replace(/&/g, "＆").replace(/</g, "‹").replace(/>/g, "›")
}

function validUrl(value, pattern) {
  if (typeof value !== "string" || value.length > urlLimit || /[^\x21-\x7e]/.test(value)) return ""
  if (!pattern.test(value) || /%(?![0-9a-f]{2})|%(?:0[0-9a-f]|1[0-9a-f]|7f|5c)/i.test(value)) return ""
  return value
}

function sourceUrl(value) {
  return validUrl(value, /^https:\/\/(?:soundcloud\.com|api-v2\.soundcloud\.com)\/[A-Za-z0-9._~!$&'()*+,;=:@%\/-]+(?:\?[A-Za-z0-9._~!$&'()*+,;=:@%\/?-]*)?$/)
}

function artworkUrl(value) {
  return validUrl(value, /^https:\/\/(?:i1|a1)\.sndcdn\.com\/[A-Za-z0-9._~!$&'()*+,;=:@%\/-]+\.(?:jpg|jpeg|png|webp)(?:\?[A-Za-z0-9._~!$&'()*+,;=:@%\/?-]*)?$/)
}

function station(value, fallback) {
  var stations = ["official", "official2", "mixtapes", "balearic", "indie", "tokyo", "friday", "hangover"]
  if (stations.indexOf(value) !== -1) return value
  return stations.indexOf(fallback) !== -1 ? fallback : "official"
}

function boundedNumber(value, maximum, fallback) {
  if (typeof value !== "number" || !isFinite(value)) return fallback === undefined ? 0 : fallback
  return Math.round(Math.max(0, Math.min(maximum, value)))
}
