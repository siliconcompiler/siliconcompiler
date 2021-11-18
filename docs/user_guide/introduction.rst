Introduction
===================================

SiliconCompiler ("SC") is an open source compiler infrastructure project that
aims to lower the barrier to custom silicon.

Motivation
-----------

Silicon had an enormous positive impact on the world the last 50 years and it's a social imperative that we surf the exponential Moore's Law as long as possible. With scaling coming to an end, the only viable path forward is extreme hardware specialization. The SiliconCompiler project aims to enable a long tail of future energy critical embedded applications by making silicon just another target for a software compiler.

Our Approach
-------------

The SiliconCompiler is a "meta" compiler infrastructure project that helps faciliate the integration of different hardware compilation tools. Core development areas for the project include:

1. A unified database (:ref:`Schema`) that enables arbitrary combinations of design, tools, and PDKs.
2. A parallel programming model (:ref:`Core API`) for distributed cloud scale hardware compilation
3. A client-server compilation model (:ref:`Remote Processing`)
