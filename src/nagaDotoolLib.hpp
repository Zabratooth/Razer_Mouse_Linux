#pragma once

#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <stdexcept>
#include <string_view>

namespace nagaDotool
{
	inline std::mutex nagaDotoolPipeMutex;
	inline FILE *nagaDotoolPipe = nullptr;

	inline void closeNagaDotoolPipe()
	{
		std::lock_guard<std::mutex> lock(nagaDotoolPipeMutex);
		if (nagaDotoolPipe)
		{
			pclose(nagaDotoolPipe);
			nagaDotoolPipe = nullptr;
		}
	}

	inline void writeNagaDotoolCommand(std::string_view command)
	{
		std::lock_guard<std::mutex> lock(nagaDotoolPipeMutex);
		if (fwrite(command.data(), 1, command.size(), nagaDotoolPipe) != command.size() ||
			fputc('\n', nagaDotoolPipe) == EOF)
		{
			return;
		}

		if (fflush(nagaDotoolPipe) == EOF)
		{
			return;
		}
	}

	inline void initNagaDotoolPipe()
	{
		std::lock_guard<std::mutex> lock(nagaDotoolPipeMutex);
		if (nagaDotoolPipe)
		{
			return;
		}

		nagaDotoolPipe = popen("nagaDotoolc", "w");
		if (!nagaDotoolPipe)
		{
			return;
		}
		setvbuf(nagaDotoolPipe, nullptr, _IOLBF, 0);
		atexit(closeNagaDotoolPipe);
	}
}
