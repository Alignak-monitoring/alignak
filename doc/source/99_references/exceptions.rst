Exceptions
==========

Exception class diagram in Alignak
-----------------------------------

Simple Exception class diagram :

.. inheritance-diagram:: __builtin__.Exception
                        alignak.http_daemon.InvalidWorkDir  alignak.http_daemon.PortNotFree
                        alignak.http_client.HTTPException  alignak.satellite.NotWorkerMod
                        alignak.webui.bottlecore.BottleException  alignak.webui.bottlecore.HTTPResponse
                        alignak.webui.bottlecore.HTTPError  alignak.webui.bottlecore.RouteError
                        alignak.webui.bottlecore.RouteReset  alignak.webui.bottlecore.RouteSyntaxError
                        alignak.webui.bottlecore.RouteBuildError  alignak.webui.bottlecore.TemplateError
                        alignak.webui.bottlewebui.BottleException  alignak.webui.bottlewebui.HTTPResponse
                        alignak.webui.bottlewebui.HTTPError  alignak.webui.bottlewebui.RouteError
                        alignak.webui.bottlewebui.RouteReset  alignak.webui.bottlewebui.RouteSyntaxError
                        alignak.webui.bottlewebui.RouteBuildError  alignak.webui.bottlewebui.TemplateError
                        alignak.daemon.InvalidPidFile
   :parts: 3
