# Pipeline - Generate documetation

Documentation is generated with every merged PR to master branch.
Pipeline is located in same jenkins as gate-check: https://10.157.93.189/job/medusa-docs/
Generated site is pushed to gh-pages branch.
GitHub Pages are setup to expose this site on https://pages.github.hpe.com/nimble/qa_automation/.

To trigger pipeline 'Generic Webhook Trigger' jenkins plugin is used with:
Post content parameters -> IF_MERGED = pull_request.merged [JSONPath]
Token -> WEBHOOK-TOKEN
Optional filter -> true = $IF_MERGED

Github qa_automation webhook:
https://10.157.93.189/generic-webhook-trigger/invoke?token=WEBHOOK-TOKEN [application/json]
individual events -> Pull requests
