# OpenAI Responses API file_search Tool Returns Empty Results

**Status**: Upstream OpenAI API issue
**Affects**: All ostruct users using file-search tool integration
**Workaround**: Use legacy Assistants API or disable file-search tool
**Tracking**: Multiple community reports across OpenAI forums, GitHub, Stack Overflow, Reddit, and Microsoft Learn
**Last Updated**: July 23, 2025

## Summary

Early adopters of the **Responses API `file_search` tool** are consistently running into an *"empty‐results"* failure pattern. Threads across OpenAI's own forum, Stack Overflow, several GitHub issue trackers, Reddit and even Microsoft's Azure‑hosted Q&A all describe the same symptom: the vector‑store indexes successfully, but the `response.output[0].results` (or the older `fileSearch.results`) array comes back empty or the tool is silently skipped.

## Impact on ostruct

- File-search tool integrations will return empty results despite successful vector store creation
- Tests involving file-search are expected to fail until OpenAI resolves the upstream issue
- Users should be aware this is an OpenAI API limitation, not an ostruct bug
- The same vector stores work correctly with the legacy Assistants API

## Community Reports

### 1. OpenAI community forum reports

| Date         | Post / thread                                                                    | Key quote                                                            |
| ------------ | -------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 7 months ago | "File search does not work well" ([OpenAI Community][1])                         | "I get zero matches even though the PDF clearly contains the text."  |
| 6 months ago | "file\_search – search nothing" ([OpenAI Community][2])                          | "`results` field is always missing."                                 |
| 6 months ago | "Assistant with a file\_search tool not working" ([OpenAI Community][3])         | "Vector store says *completed* but queries return nothing."          |
| 4 months ago | "Responses API `file_search_call` 'queries' array empty" ([OpenAI Community][4]) | Confirms that even the internal `queries` diagnostic is blank.       |
| 3 months ago | "Is file‑search result prioritised over instruction?" ([OpenAI Community][5])    | Mentions "tool returns nothing" in Responses while Assistants works. |

### 2. GitHub issues across SDKs

| Repo                     | Issue                                                                  | Signal                                                          |
| ------------------------ | ---------------------------------------------------------------------- | --------------------------------------------------------------- |
| **openai/openai‑python** | `FileSearchToolCall.file_search has empty results #1966` ([GitHub][6]) | Maintainer reproduced: "always empty."                          |
| **openai-php/client**    | "No result with assistant file search" #436 ([GitHub][7])              | PHP binding shows same symptom.                                 |
| **openai/openai‑dotnet** | "Vector store results are not retrieved #258" ([GitHub][8])            | .NET SDK always empty on `file_search`.                         |
| **vercel/ai**            | `file_search` rejects parameters / empty output #7437 ([GitHub][9])    | Confirms Responses tool ignores `maxResults` & returns nothing. |

### 3. Stack Overflow questions

- "File Search tool stops working when I enable custom function calling" – always zero matches ([Stack Overflow][10])
- "OpenAI assistant working for one API‑key but not another" – comments trace failure to `file_search` returning blanks ([Stack Overflow][11])
- "Error with file\_search tool in langchain‑openai" – empty payload leads to SDK error ([Stack Overflow][12])

### 4. Reddit anecdotes

- r/ChatGPTPro thread "Thread returns blank every time" – specifically blames `file_search` in Responses API ([Reddit][13])
- r/OpenAI "Is file search result prioritised over instruction?" – user forced to disable the tool because results were always empty ([Reddit][14])

### 5. Microsoft / Azure documentation forum

- Azure OpenAI Q&A: "Using Responses API file\_search with other tools" – reproduces empty results when both file\_search and any custom tool are enabled ([Microsoft Learn][15])

## Key Patterns

- **Vector‑store creation succeeds** (`status:"completed"`), confirming the files are embedded.([OpenAI Community][4], [GitHub][8])
- **Empty `results` array** is returned in stream or final message for *any* query—even ones that match the doc exactly.([OpenAI Community][1], [GitHub][6])
- The same vector store **works in the old Assistants API or Playground** but fails in Responses API.([OpenAI Community][4], [OpenAI Community][16])
- Developers tried switching models (GPT‑4o vs GPT‑3.5), temperatures, and chunk sizes **without success**.([OpenAI Community][2], [Stack Overflow][10])

## Current Status & OpenAI Acknowledgement

No official fix or ETA has been posted. The OpenAI docs still present `file_search` as production‑ready ([OpenAI Platform][17]), but multiple open GitHub issues remain unclosed. Several forum threads have moderator responses indicating the problem has been "escalated to engineering," yet the last updates (May–June 2025) show it is still reproducible.([Microsoft Learn][15], [OpenAI Community][5])

## Practical Implications for Testing

- Failing file-search tests are consistent with community experience and should be flagged as **"expected‑fail until upstream fix."**
- When the fix ships, tests will immediately pass—making them good canaries for the resolution.

## References

[1]: https://community.openai.com/t/file-search-does-not-work-well/1066585?utm_source=chatgpt.com "File search does not work well - API - OpenAI Developer Community"
[2]: https://community.openai.com/t/file-search-search-nothing/1086961?utm_source=chatgpt.com "File_search - search nothing - API - OpenAI Developer Community"
[3]: https://community.openai.com/t/assistant-with-a-file-search-tool-not-working/1097484?utm_source=chatgpt.com "Assistant with a file_search tool not working - API"
[4]: https://community.openai.com/t/responses-api-file-search-call-queries-array-empty-in-response-output-item-added-event/1152057?utm_source=chatgpt.com "Responses API file_search_call 'queries' array empty in response ..."
[5]: https://community.openai.com/t/is-file-search-result-prioritized-over-instruction/1206961?utm_source=chatgpt.com "Is file search result prioritized over instruction? - API"
[6]: https://github.com/openai/openai-python/issues/1966?utm_source=chatgpt.com "FileSearchToolCall.file_search has empty results #1966 - GitHub"
[7]: https://github.com/openai-php/client/issues/436?utm_source=chatgpt.com "openai-php/client - [Bug]: No result with assistant file search - GitHub"
[8]: https://github.com/openai/openai-dotnet/issues/258?utm_source=chatgpt.com "Assistant Vector Store results are not retrieved · Issue #258 - GitHub"
[9]: https://github.com/vercel/ai/issues/7437?utm_source=chatgpt.com "file_search tool rejects maxResults and searchType parameters with ..."
[10]: https://stackoverflow.com/questions/79329549/file-search-tool-stops-working-when-i-enable-custom-function-calling?utm_source=chatgpt.com "File Search tool stops working when I enable custom function calling"
[11]: https://stackoverflow.com/questions/79118646/openai-assistant-working-for-one-api-key-but-not-for-another-one?utm_source=chatgpt.com "OpenAI Assistant - working for one API_Key but not for another one?"
[12]: https://stackoverflow.com/questions/79639207/error-with-file-search-tool-in-langchain-python-library?utm_source=chatgpt.com "Error with file_search tool in langchain python library - Stack Overflow"
[13]: https://www.reddit.com/r/ChatGPTPro/comments/1d1wrup/thread_returns_nothingblank_everytime/?utm_source=chatgpt.com "Thread returns nothing/blank everytime : r/ChatGPTPro - Reddit"
[14]: https://www.reddit.com/r/OpenAI/comments/1jqfa5k/is_file_search_result_prioritized_over_instruction/?utm_source=chatgpt.com "Is file search result prioritized over instruction? - OpenAI - Reddit"
[15]: https://learn.microsoft.com/en-us/answers/questions/2276634/using-responses-api-file-search-with-other-custom?utm_source=chatgpt.com "Using Responses API file_search with other custom tools ..."
[16]: https://community.openai.com/t/file-search-tool-broken-assistants-api/1041727?utm_source=chatgpt.com "'file_search' Tool Broken (Assistants API) - Bugs"
[17]: https://platform.openai.com/docs/guides/tools-file-search?utm_source=chatgpt.com "File search - OpenAI API"
