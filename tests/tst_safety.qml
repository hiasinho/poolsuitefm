import QtQuick
import QtTest
import "../Safety.js" as Safety

TestCase {
  name: "PoolsuiteSafety"

  function test_urlPolicy_data() {
    var request = new XMLHttpRequest()
    request.open("GET", Qt.resolvedUrl("url_cases.json"), false)
    request.send()
    return JSON.parse(request.responseText)
  }

  function test_urlPolicy(data) {
    var result = data.kind === "source" ? Safety.sourceUrl(data.value) : Safety.artworkUrl(data.value)
    compare(result, data.valid ? data.value : "")
  }

  function test_urlLengths() {
    var prefix = "https://i1.sndcdn.com/"
    var url = prefix + "a".repeat(Safety.urlLimit - prefix.length - 4) + ".jpg"
    compare(Safety.artworkUrl(url), url)
    compare(Safety.artworkUrl(url + "a"), "")
    prefix = "https://soundcloud.com/"
    url = prefix + "a".repeat(Safety.urlLimit - prefix.length)
    compare(Safety.sourceUrl(url), url)
    compare(Safety.sourceUrl(url + "a"), "")
  }

  function test_boundedObjectParsing() {
    compare(Safety.parseObject('{"running":true}').running, true)
    var invalid = [null, {}, "null", "[]", "42", "true", "broken", '{"title":"' + "x".repeat(Safety.outputLimit) + '"}']
    for (var i = 0; i < invalid.length; i++) compare(Safety.parseObject(invalid[i]), null)
  }

  function test_displayBoundary() {
    compare(Safety.displayText("<b>Title</b>\x1b\n\u202e end"), "<b>Title</b> end")
    compare(Safety.displayText("x".repeat(1000)).length, Safety.textLimit)
    compare(Safety.displayText({ title: "bad" }), "")
    compare(Safety.displayText(["bad"]), "")
    compare(Safety.displayText("🌴"), "🌴")
    compare(Safety.displayText("\ud800"), "")
    compare(Safety.displayText("a".repeat(255) + "🌴"), "a".repeat(255))
  }

  function test_plainTooltip() {
    var text = Safety.tooltip('<img src="file:///tmp/test.png"> &lt;b&gt;\u202e\nArtist')
    verify(text.indexOf("<") === -1)
    verify(text.indexOf(">") === -1)
    verify(text.indexOf("&") === -1)
    verify(text.indexOf("\u202e") === -1)
    verify(text.indexOf("\n") === -1)
    compare(Safety.tooltip("x".repeat(1000)).length, Safety.tooltipLimit)
    compare(Safety.tooltip("Artist — Title"), "Artist — Title")
  }

  function test_numbersAndStation() {
    var invalid = [null, "100", [], {}, true, NaN, Infinity, -Infinity]
    for (var i = 0; i < invalid.length; i++) compare(Safety.boundedNumber(invalid[i], 100, 70), 70)
    compare(Safety.boundedNumber(12345, 100), 100)
    compare(Safety.boundedNumber(-1, 100), 0)
    compare(Safety.boundedNumber(42.2, 100), 42)
    compare(Safety.boundedNumber(1e10, Safety.timeLimit), Safety.timeLimit)
    compare(Safety.station("tokyo", "official"), "tokyo")
    compare(Safety.station("unknown", "mixtapes"), "mixtapes")
    compare(Safety.station({}, "unknown"), "official")
  }
}
